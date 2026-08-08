#!/usr/bin/env python3
"""
Evidence-degradation experiment for the Evidence Debt paper (v2).

v2 changes relative to v1 (in response to internal adversarial review):
  * Implementation-invariant effort accounting: all exact and redundant key
    joins are O(1) index lookups contributing zero effort; effort is counted
    ONLY at heuristic decision points, as (a) the number of links requiring
    non-exact resolution ("fallback links") and (b) candidate records
    examined at those points.
  * Two irrecoverability constructs, scored separately:
      - record loss: a required record no longer exists in any store;
      - identifiability-based irrecoverability (Definition 5 faithful):
        a link is irrecoverable if the parent record is destroyed, OR no
        key path survives AND the attribute discriminators (service, actor
        where applicable, timestamps) cannot uniquely identify the true
        parent (missing timestamps, truth outside the candidate window, or
        a non-singleton candidate set).
  * A pairwise arm (correlation_ids + timestamps) for coverage interaction,
    plus a paired per-link path census that directly tests Proposition 2's
    acceptable-path premise on identical records and degradation masks.
  * Sensitivity arms that can move the conclusions: heuristic window 24 h
    (below the 36 h max true gap), redundancy disabled in the generator,
    ticket filer != commit author for 30% of chains, and a single-knob
    density sweep (chains/service in {50,100,150}, other knobs fixed).
  * ED(t) computed end-to-end under a declared synthetic workload
    (per-configuration six-link audit workload, one unit-weight subquery per
    required link): excess
    resolution cost (fallback links + 0.01 * candidates examined, in
    declared resolution units), an error penalty LAMBDA=25 per returned false
    link. Acceptance is decided before ground truth: exact/redundant joins and
    unique heuristic candidates are accepted; ambiguous heuristic candidates may
    be retained internally for diagnosis but the policy abstains. The
    preregistered reporting policy then partitions outcomes into supported-correct,
    accepted-wrong, and policy-abstention, so error and abstention penalties
    are mutually exclusive. Complete-corpus baseline cost/error/
    irrecoverability = 0 by construction (all joins exact).
  * results table rows and all figure series emitted programmatically.

Deterministic given SEEDS. Pure stdlib.
"""

import copy, csv, math, random, statistics, time, os

SEEDS = list(range(20))
LEVELS = [0.0, 0.01, 0.05, 0.10, 0.20, 0.40]
CLASSES = ["intent_links", "approval_links", "correlation_ids",
           "source_artifacts", "timestamps", "ids_plus_timestamps",
           "combined"]

N_SERVICES = 8
DAY = 24.0
PI_ABSTENTION = 50.0    # declared penalty per policy abstention
LAMBDA_ERROR = 25.0     # declared consequence penalty per returned wrong link
PI_SENSITIVITY = [0.0, 1.0, 10.0, 25.0, 50.0, 100.0]
WEIGHT_GRID = [0.0, 10.0, 25.0, 50.0, 100.0]
CAND_COST = 0.01        # declared cost per candidate examined
FALLBACK_COST = 1.0     # declared cost per link needing non-exact resolution

PROFILES = {
    "sparse": dict(chains_per_service=50, n_actors=12, window_days=180.0),
    "dense":  dict(chains_per_service=150, n_actors=6, window_days=90.0),
    # single-knob density sweep (used by sensitivity runs only)
    "mid1":   dict(chains_per_service=50,  n_actors=12, window_days=180.0),
    "mid2":   dict(chains_per_service=100, n_actors=12, window_days=180.0),
    "mid3":   dict(chains_per_service=150, n_actors=12, window_days=180.0),
}

LINKS = ["intent", "approval", "build", "artifact", "deploy", "config"]


# ----------------------------------------------------------------- generation
def generate(rng, profile, redundancy=True, filer_mismatch=0.0):
    prof = PROFILES[profile]
    stores = {s: [] for s in
              ["ticket", "commit", "approval", "build", "artifact",
               "deploy", "config"]}
    truth = {}
    actors = [f"actor{i}" for i in range(prof["n_actors"])]
    cid = 0
    for svc_i in range(N_SERVICES):
        svc = f"svc{svc_i}"
        for _ in range(prof["chains_per_service"]):
            cid += 1
            t0 = rng.uniform(0, prof["window_days"]) * DAY
            author = rng.choice(actors)
            if filer_mismatch > 0 and rng.random() < filer_mismatch:
                filer = rng.choice([a for a in actors if a != author])
            else:
                filer = author
            approver = rng.choice([a for a in actors if a != author])
            tkt, sha, bid = f"TKT-{cid}", f"sha-{cid}", f"bld-{cid}"
            dig, dep, cfg = f"dig-{cid}", f"dep-{cid}", f"cfg-{cid}"
            t1 = t0 + rng.uniform(0.5, 24)
            t2 = t1 + rng.uniform(0.2, 12)
            t3 = t2 + rng.uniform(0.1, 4)
            t4 = t3 + rng.uniform(0.05, 1)
            t5 = t4 + rng.uniform(0.5, 36)
            t6 = t5 + rng.uniform(0.01, 0.5)
            stores["ticket"].append(dict(key=tkt, svc=svc, actor=filer,
                                         ts=t0, chain=cid))
            stores["commit"].append(dict(key=sha, svc=svc, actor=author,
                                         ts=t1, ticket_ref=tkt, chain=cid))
            stores["approval"].append(dict(key=f"apr-{cid}", svc=svc,
                                           actor=approver, ts=t2,
                                           commit_ref=sha, chain=cid))
            b = dict(key=bid, svc=svc, actor="ci-bot", ts=t3,
                     commit_ref=sha, chain=cid)
            if redundancy:
                b["digest_ref"] = dig
            stores["build"].append(b)
            stores["artifact"].append(dict(key=dig, svc=svc, actor="ci-bot",
                                           ts=t4, build_ref=bid, chain=cid))
            stores["deploy"].append(dict(key=dep, svc=svc, actor="cd-bot",
                                         ts=t5, digest_ref=dig, chain=cid))
            c = dict(key=cfg, svc=svc, actor="cd-bot", ts=t6,
                     deploy_ref=dep, chain=cid)
            if redundancy:
                c["digest_ref"] = dig
            stores["config"].append(c)
            truth[cid] = dict(intent=(sha, tkt), approval=(f"apr-{cid}", sha),
                              build=(bid, sha), artifact=(dig, bid),
                              deploy=(dep, dig), config=(cfg, dep),
                              filer=filer, author=author)
    return stores, truth


# ---------------------------------------------------------------- degradation
def degrade(stores, cls, p, rng):
    def hit():
        return rng.random() < p

    strip_intent = cls in ("intent_links", "combined")
    strip_approval = cls in ("approval_links", "combined")
    strip_ids = cls in ("correlation_ids", "ids_plus_timestamps", "combined")
    delete_records = cls in ("source_artifacts", "combined")
    null_ts = cls in ("timestamps", "ids_plus_timestamps", "combined")

    if strip_intent:
        for r in stores["commit"]:
            if hit():
                r["ticket_ref"] = None
    if strip_approval:
        for r in stores["approval"]:
            if hit():
                r["commit_ref"] = None
    if strip_ids:
        for r in stores["build"]:
            if hit():
                r["commit_ref"] = None
            if "digest_ref" in r and hit():
                r["digest_ref"] = None
        for r in stores["artifact"]:
            if hit():
                r["build_ref"] = None
        for r in stores["deploy"]:
            if hit():
                r["digest_ref"] = None
        for r in stores["config"]:
            if hit():
                r["deploy_ref"] = None
            if "digest_ref" in r and hit():
                r["digest_ref"] = None
    if delete_records:
        for st in ["ticket", "commit", "approval", "build", "artifact",
                   "deploy"]:
            stores[st] = [r for r in stores[st] if not hit()]
    if null_ts:
        for st in stores:
            for r in stores[st]:
                if hit():
                    r["ts"] = None


def paired_path_corpora(profile, p, seed):
    """Return paired ID-only, timestamp-only, and union degradations.

    The three corpora start from the same generated estate.  The identifier and
    timestamp masks are sampled once and then applied separately and jointly,
    making the per-link Proposition-2 antecedent directly testable.
    """
    base, truth = generate(random.Random(1000 + seed), profile)
    ids_only, time_only, union = (copy.deepcopy(base) for _ in range(3))

    id_rng = random.Random(17000 + seed * 131 + int(p * 1000))
    time_rng = random.Random(23000 + seed * 131 + int(p * 1000))
    id_fields = {
        "build": ("commit_ref", "digest_ref"),
        "artifact": ("build_ref",),
        "deploy": ("digest_ref",),
        "config": ("deploy_ref", "digest_ref"),
    }
    id_mask = set()
    for store, fields in id_fields.items():
        for record in base[store]:
            for field in fields:
                if field in record and id_rng.random() < p:
                    id_mask.add((store, record["key"], field))
    time_mask = set()
    for store in base:
        for record in base[store]:
            if time_rng.random() < p:
                time_mask.add((store, record["key"]))

    def apply_masks(stores, apply_ids, apply_time):
        by_key = {store: {r["key"]: r for r in records}
                  for store, records in stores.items()}
        if apply_ids:
            for store, key, field in id_mask:
                by_key[store][key][field] = None
        if apply_time:
            for store, key in time_mask:
                by_key[store][key]["ts"] = None

    apply_masks(ids_only, True, False)
    apply_masks(time_only, False, True)
    apply_masks(union, True, True)
    return ids_only, time_only, union, truth


# ------------------------------------------------------------- reconstruction
class Rebuilder:
    """All exact/redundant joins are O(1) index lookups (zero counted
    effort). Effort is counted only at heuristic decision points."""

    def __init__(self, stores, window_h=48.0):
        self.stores = stores
        self.window_h = window_h
        self.by_key = {s: {r["key"]: r for r in rs}
                       for s, rs in stores.items()}
        self.by_svc = {}
        for s, rs in stores.items():
            d = {}
            for r in rs:
                d.setdefault(r["svc"], []).append(r)
            self.by_svc[s] = d
        # reverse indexes for exact/redundant joins (implementation detail;
        # contributes no counted effort)
        self.apr_by_commit = {}
        for r in stores["approval"]:
            if r.get("commit_ref"):
                self.apr_by_commit.setdefault(r["commit_ref"], r)
        self.build_by_digest = {}
        for r in stores["build"]:
            if r.get("digest_ref"):
                self.build_by_digest.setdefault(r["digest_ref"], r)
        self.deploy_by_digest = {}
        for r in stores["deploy"]:
            if r.get("digest_ref"):
                self.deploy_by_digest.setdefault(r["digest_ref"], r)
        self.candidates_examined = 0
        self.fallback_links = 0

    def _exact(self, store, key):
        if key is None:
            return None
        return self.by_key[store].get(key)

    def _heur(self, store, child, actor_match=None):
        """Heuristic linkage. Counts effort. Returns (record, ambiguous)."""
        self.fallback_links += 1
        if child.get("ts") is None:
            return None, False
        cands = []
        for r in self.by_svc[store].get(child["svc"], []):
            self.candidates_examined += 1
            if r.get("ts") is None:
                continue
            dt = child["ts"] - r["ts"]
            if 0 < dt <= self.window_h:
                if actor_match and r["actor"] != actor_match:
                    continue
                cands.append((dt, r))
        if not cands:
            return None, False
        cands.sort(key=lambda x: x[0])
        return cands[0][1], len(cands) > 1

    def rebuild_chain(self, config):
        """Return candidate keys and policy acceptance decisions.

        Acceptance uses only corpus-visible evidence. Ground truth is not passed to
        this method and is consulted later solely to score accepted answers.
        """
        out, accepted = {}, {}
        dep = self._exact("deploy", config.get("deploy_ref"))
        dep_accepted = dep is not None
        if dep is None and config.get("digest_ref"):
            dep = self.deploy_by_digest.get(config["digest_ref"])
            dep_accepted = dep is not None
        if dep is None:
            dep, ambiguous = self._heur("deploy", config)
            dep_accepted = dep is not None and not ambiguous
        out["config"] = dep["key"] if dep else None
        accepted["config"] = dep_accepted

        art = None
        art_accepted = False
        if dep is not None:
            art = self._exact("artifact", dep.get("digest_ref"))
            art_accepted = dep_accepted and art is not None
        if art is None and config.get("digest_ref"):
            art = self._exact("artifact", config.get("digest_ref"))
            art_accepted = art is not None
        if art is None and dep is not None:
            art, ambiguous = self._heur("artifact", dep)
            art_accepted = dep_accepted and art is not None and not ambiguous
        out["deploy"] = art["key"] if art else None
        accepted["deploy"] = art_accepted

        bld = None
        bld_accepted = False
        if art is not None:
            bld = self._exact("build", art.get("build_ref"))
            bld_accepted = art_accepted and bld is not None
            if bld is None:
                bld = self.build_by_digest.get(art["key"])
                bld_accepted = art_accepted and bld is not None
            if bld is None:
                bld, ambiguous = self._heur("build", art)
                bld_accepted = art_accepted and bld is not None and not ambiguous
        out["artifact"] = bld["key"] if bld else None
        accepted["artifact"] = bld_accepted

        com = None
        com_accepted = False
        if bld is not None:
            com = self._exact("commit", bld.get("commit_ref"))
            com_accepted = bld_accepted and com is not None
            if com is None:
                com, ambiguous = self._heur("commit", bld)
                com_accepted = bld_accepted and com is not None and not ambiguous
        out["build"] = com["key"] if com else None
        accepted["build"] = com_accepted

        apr = None
        apr_accepted = False
        if com is not None:
            apr = self.apr_by_commit.get(com["key"])
            apr_accepted = com_accepted and apr is not None
            if apr is None:
                fake_child = dict(svc=com["svc"],
                                  ts=(com["ts"] + self.window_h / 2
                                      if com.get("ts") is not None else None))
                apr, ambiguous = self._heur("approval", fake_child)
                apr_accepted = com_accepted and apr is not None and not ambiguous
        out["approval"] = apr["key"] if apr else None
        accepted["approval"] = apr_accepted

        tkt = None
        tkt_accepted = False
        if com is not None:
            tkt = self._exact("ticket", com.get("ticket_ref"))
            tkt_accepted = com_accepted and tkt is not None
            if tkt is None:
                tkt, ambiguous = self._heur("ticket", com, actor_match=com["actor"])
                tkt_accepted = com_accepted and tkt is not None and not ambiguous
        out["intent"] = tkt["key"] if tkt else None
        accepted["intent"] = tkt_accepted
        return out, accepted


# -------------------------------------------- identifiability irrecoverability
def link_irrecoverable(link, cfgrec, tr, surviving_rec, by_svc, window_h):
    """Definition-5-faithful, closed-world: parent destroyed, OR no key path
    survives AND discriminators cannot uniquely identify the true parent."""
    parent_store = dict(config="deploy", deploy="artifact", artifact="build",
                        build="commit", approval="approval", intent="ticket")
    st = parent_store[link]
    exp_key = dict(config=tr["config"][1], deploy=tr["deploy"][1],
                   artifact=tr["artifact"][1], build=tr["build"][1],
                   approval=tr["approval"][0], intent=tr["intent"][1])[link]
    parent = surviving_rec[st].get(exp_key)
    if parent is None:
        return True                                  # record loss
    # does any key path survive? (link-specific)
    def key_path():
        if link == "config":
            if cfgrec.get("deploy_ref"):
                return True
            dig = cfgrec.get("digest_ref")
            return bool(dig and parent.get("digest_ref") == dig)
        if link == "deploy":
            child = surviving_rec["deploy"].get(tr["config"][1])
            if child is not None and child.get("digest_ref"):
                return True
            return bool(cfgrec.get("digest_ref"))
        if link == "artifact":
            child = surviving_rec["artifact"].get(tr["deploy"][1])
            if child is not None and child.get("build_ref"):
                return True
            return bool(parent.get("digest_ref"))
        if link == "build":
            child = surviving_rec["build"].get(tr["artifact"][1])
            return bool(child is not None and child.get("commit_ref"))
        if link == "approval":
            return bool(parent.get("commit_ref"))
        if link == "intent":
            child = surviving_rec["commit"].get(tr["intent"][0])
            return bool(child is not None and child.get("ticket_ref"))
        return False
    if key_path():
        return False
    # heuristic identifiability: child record with a timestamp, parent with a
    # timestamp, truth uniquely in window
    child_key = dict(config=cfgrec["key"], deploy=tr["config"][1],
                     artifact=tr["deploy"][1], build=tr["artifact"][1],
                     approval=tr["build"][1], intent=tr["intent"][0])[link]
    child_store = dict(config="config", deploy="deploy", artifact="artifact",
                       build="build", approval="commit", intent="commit")[link]
    child = surviving_rec[child_store].get(child_key)
    if child is None or child.get("ts") is None or parent.get("ts") is None:
        return True
    actor_match = child["actor"] if link == "intent" else None
    n_in_window = 0
    truth_in = False
    for r in by_svc[st].get(child["svc"], []):
        if r.get("ts") is None:
            continue
        dt = child["ts"] - r["ts"]
        if 0 < dt <= window_h:
            if actor_match and r["actor"] != actor_match:
                continue
            n_in_window += 1
            if r["key"] == exp_key:
                truth_in = True
    return (not truth_in) or n_in_window != 1


def path_state(stores, truth, window_h=48.0):
    """Return link-level acceptable-path state keyed by (chain, link)."""
    surviving = {s: {r["key"]: r for r in records}
                 for s, records in stores.items()}
    by_svc = {}
    for store, records in stores.items():
        grouped = {}
        for record in records:
            grouped.setdefault(record["svc"], []).append(record)
        by_svc[store] = grouped
    state = {}
    for cfgrec in stores["config"]:
        cid = cfgrec["chain"]
        for link in LINKS:
            state[(cid, link)] = not link_irrecoverable(
                link, cfgrec, truth[cid], surviving, by_svc, window_h
            )
    return state


def run_pairwise_path_diagnostic(p, seed, profile):
    """Measure the exact path-survival premise of Proposition 2 per link."""
    ids, timestamps, union, truth = paired_path_corpora(profile, p, seed)
    a = path_state(ids, truth)
    b = path_state(timestamps, truth)
    ab = path_state(union, truth)
    keys = sorted(a)
    premise = sum(a[k] and b[k] for k in keys)
    only_union_loss = sum(a[k] and b[k] and not ab[k] for k in keys)
    return dict(
        profile=profile,
        p=p,
        seed=seed,
        total_links=len(keys),
        ids_usable=sum(a.values()),
        time_usable=sum(b.values()),
        union_usable=sum(ab.values()),
        premise_links=premise,
        only_union_loss=only_union_loss,
        premise_rate=premise / len(keys),
        only_union_loss_rate=only_union_loss / len(keys),
        conditional_loss=(only_union_loss / premise) if premise else 0.0,
    )


# -------------------------------------------------------------------- scoring
def classify_outcome(accepted, candidate_key, expected_key):
    """Apply the preregistered S/W/N rule after a corpus-only accept decision."""
    if not accepted:
        return "N"
    return "S" if candidate_key == expected_key else "W"


def run_condition(cls, p, seed, profile, window_h=48.0, redundancy=True,
                  filer_mismatch=0.0, tag=""):
    rng = random.Random(1000 + seed)
    stores, truth = generate(rng, profile, redundancy=redundancy,
                             filer_mismatch=filer_mismatch)
    dr = random.Random(9000 + seed * 131 + int(p * 1000))
    degrade(stores, cls, p, dr)

    surviving_rec = {s: {r["key"]: r for r in rs} for s, rs in stores.items()}
    reported_store = dict(config="deploy", deploy="artifact",
                          artifact="build", build="commit",
                          approval="approval", intent="ticket")

    rb = Rebuilder(stores, window_h=window_h)
    t_start = time.perf_counter()
    correct = false = no_cert = 0
    chains_ok = n_chains = 0
    chains_recloss = chains_irrec = 0
    error_links_total = irrec_links_total = no_cert_links_total = 0
    ed_effort = ed_error = ed_abstention = 0.0
    for cfgrec in stores["config"]:
        cid = cfgrec["chain"]
        n_chains += 1
        fb0, cand0 = rb.fallback_links, rb.candidates_examined
        got, policy_accepts = rb.rebuild_chain(cfgrec)
        fb1, cand1 = rb.fallback_links, rb.candidates_examined
        tr = truth[cid]
        expected = dict(config=tr["config"][1], deploy=tr["deploy"][1],
                        artifact=tr["artifact"][1], build=tr["build"][1],
                        approval=tr["approval"][0], intent=tr["intent"][1])
        ok_all, recloss, irrec_any = True, False, False
        irrec_links = no_cert_links = false_links = 0
        for link in LINKS:
            exp, gotk = expected[link], got[link]
            if exp not in surviving_rec[reported_store[link]]:
                recloss = True
            is_irrec = link_irrecoverable(
                link, cfgrec, tr, surviving_rec, rb.by_svc, window_h
            )
            if is_irrec:
                irrec_any = True
                irrec_links += 1
            # The acceptance decision was already made by Rebuilder without
            # access to ground truth. Truth is consulted only after that decision
            # to distinguish supported-correct (S) from accepted-wrong (W).
            outcome = classify_outcome(policy_accepts[link], gotk, exp)
            if outcome == "N":
                no_cert += 1
                no_cert_links += 1
                ok_all = False
            elif outcome == "S":
                correct += 1
            else:
                false += 1
                false_links += 1
                ok_all = False
        chains_ok += ok_all
        chains_recloss += recloss
        chains_irrec += irrec_any
        error_links_total += false_links
        irrec_links_total += irrec_links
        no_cert_links_total += no_cert_links
        # ED under the declared workload: six unit-weight link subqueries per
        # config; complete-corpus cost is 0 (all joins exact)
        ed_effort += FALLBACK_COST * (fb1 - fb0) + CAND_COST * (cand1 - cand0)
        ed_error += LAMBDA_ERROR * false_links
        ed_abstention += PI_ABSTENTION * no_cert_links
    elapsed = time.perf_counter() - t_start
    total_links = n_chains * len(LINKS)
    accepted = correct + false
    return dict(
        tag=tag or "main", profile=profile, cls=cls, p=p, seed=seed,
        coverage=correct / total_links,
        false_rate=(false / accepted) if accepted else 0.0,
        chain_cov=chains_ok / n_chains,
        recloss=chains_recloss / n_chains,
        irrec=chains_irrec / n_chains,
        error_links=error_links_total / total_links,
        irrec_links=irrec_links_total / total_links,
        no_cert_links=no_cert_links_total / total_links,
        fallback=rb.fallback_links / n_chains,
        candidates=rb.candidates_examined / n_chains,
        ed_effort=ed_effort / n_chains,
        ed_error=ed_error / n_chains,
        ed_abstention=ed_abstention / n_chains,
        ed=(ed_effort + ed_error + ed_abstention) / n_chains,
        secs=elapsed,
    )


# ------------------------------------------------- interest / decay model fig
def interest_curve():
    LAM = 1.0 / 900.0
    CERT_COST = 5.0
    PI_CURVE = 100.0
    rows = []
    for day in range(0, 1096, 7):
        paths = []
        if day <= 90:
            paths.append(1.0)
        if day <= 400:
            paths.append(3.0)
        p_emp = math.exp(-LAM * day)
        c_int = 8.0 * (1 + day / 365.0)
        if paths:
            attempt_cost, p_err, p_irr = min(paths), 0.0, 0.0
        else:
            attempt_cost = p_emp * c_int + (1 - p_emp) * CERT_COST
            p_err = 0.0
            p_irr = 1 - p_emp
        burden = (attempt_cost + LAMBDA_ERROR * p_err
                  + PI_CURVE * p_irr)
        rows.append((day, attempt_cost, p_err, p_irr, burden))
    return rows


# ----------------------------------------------------------------------- main
def agg_rows(rows, keys):
    agg = {}
    for r in rows:
        agg.setdefault(tuple(r[k] for k in keys), []).append(r)
    return agg


def mean_sd(rs, k):
    vals = [x[k] for x in rs]
    return (statistics.mean(vals),
            statistics.stdev(vals) if len(vals) > 1 else 0.0)


def write_pi_sensitivity(agg, out_dir):
    """Decompose ED and rank all seven main arms as pi varies.

    The comparison uses the dense-profile, p=40% endpoint. ``no_cert_links`` is
    stored as a fraction of the six required links, so multiplying by
    ``len(LINKS)`` recovers mutually exclusive policy-abstention outcomes per
    configuration.
    """
    labels = {
        "intent_links": "Intent",
        "approval_links": "Approval",
        "correlation_ids": "IDs",
        "source_artifacts": "Delete",
        "timestamps": "Time",
        "ids_plus_timestamps": "IDs+Time",
        "combined": "All",
    }
    output = []
    by_pi = {}
    for pi in PI_SENSITIVITY:
        cells = []
        for cls in CLASSES:
            key = ("main", "dense", cls, 0.40)
            effort = mean_sd(agg[key], "ed_effort")[0]
            error = mean_sd(agg[key], "ed_error")[0]
            irr_per_config = (mean_sd(agg[key], "no_cert_links")[0]
                              * len(LINKS))
            abstention = pi * irr_per_config
            total = effort + error + abstention
            cells.append(dict(cls=cls, effort=effort, error=error,
                              abstention=abstention, ed=total))
        ordered_totals = sorted({round(cell["ed"], 12) for cell in cells},
                                reverse=True)
        for cell in cells:
            cell["rank"] = ordered_totals.index(round(cell["ed"], 12)) + 1
            output.append(dict(profile="dense", p=0.40, pi=pi, **cell))
        by_pi[pi] = cells

    csv_path = os.path.join(out_dir, "pi_sensitivity.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["profile", "p", "pi", "cls", "effort",
                           "error", "abstention", "ed", "rank"],
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(output)

    tex_path = os.path.join(out_dir, "table_pi_sensitivity.tex")
    with open(tex_path, "w") as f:
        f.write("\\resizebox{\\textwidth}{!}{%\n")
        f.write("\\begin{tabular}{@{}rccccccc@{}}\n\\toprule\n")
        f.write("$\\pi$ & " + " & ".join(labels[c] for c in CLASSES)
                + " \\\\\n\\midrule\n")
        for pi in PI_SENSITIVITY:
            entries = []
            for cell in by_pi[pi]:
                entries.append(
                    f"{cell['effort']:.1f}/{cell['error']:.1f}/"
                    f"{cell['abstention']:.1f}/"
                    f"{cell['ed']:.1f}$^{{({cell['rank']})}}$"
                )
            f.write(f"{pi:g} & " + " & ".join(entries) + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}%\n}\n")

    compact_path = os.path.join(out_dir, "table_pi_sensitivity_compact.tex")
    with open(compact_path, "w") as f:
        f.write("\\resizebox{\\textwidth}{!}{%\n")
        f.write("\\begin{tabular}{@{}rccccccc@{}}\n\\toprule\n")
        f.write("$\\pi$ & " + " & ".join(labels[c] for c in CLASSES)
                + " \\\\\n\\midrule\n")
        for pi in (0.0, 50.0, 100.0):
            entries = []
            for cell in by_pi[pi]:
                entries.append(
                    f"{cell['effort']:.1f}/{cell['error']:.1f}/"
                    f"{cell['abstention']:.1f}/{cell['ed']:.1f}"
                    f"$^{{({cell['rank']})}}$"
                )
            f.write(f"{pi:g} & " + " & ".join(entries) + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}%\n}\n")


def write_weight_sensitivity(agg, out_dir):
    """Evaluate all seven arms on a joint lambda/pi consequence-weight grid."""
    labels = {
        "intent_links": "Intent", "approval_links": "Approval",
        "correlation_ids": "IDs", "source_artifacts": "Delete",
        "timestamps": "Time", "ids_plus_timestamps": "IDs+Time",
        "combined": "All",
    }
    rows, winners = [], {}
    for pi in WEIGHT_GRID:
        for lam in WEIGHT_GRID:
            cells = []
            for cls in CLASSES:
                key = ("main", "dense", cls, 0.40)
                effort = mean_sd(agg[key], "ed_effort")[0]
                err = mean_sd(agg[key], "error_links")[0] * len(LINKS)
                no_cert = mean_sd(agg[key], "no_cert_links")[0] * len(LINKS)
                error = lam * err
                abstention = pi * no_cert
                cells.append(dict(cls=cls, effort=effort, error=error,
                                  abstention=abstention,
                                  ed=effort + error + abstention))
            ordered = sorted({round(c["ed"], 12) for c in cells}, reverse=True)
            for cell in cells:
                cell["rank"] = ordered.index(round(cell["ed"], 12)) + 1
                rows.append(dict(profile="dense", p=0.40, lambda_=lam,
                                 pi=pi, **cell))
            winner = max(cells, key=lambda c: c["ed"])
            winners[(pi, lam)] = (labels[winner["cls"]], winner["ed"])

    with open(os.path.join(out_dir, "weight_sensitivity.csv"), "w",
              newline="") as f:
        fields = ["profile", "p", "lambda", "pi", "cls", "effort",
                  "error", "abstention", "ed", "rank"]
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for row in rows:
            row = dict(row)
            row["lambda"] = row.pop("lambda_")
            w.writerow(row)

    with open(os.path.join(out_dir, "table_weight_sensitivity.tex"), "w") as f:
        f.write("\\begin{tabular}{@{}rccccc@{}}\n\\toprule\n")
        f.write("$\\pi\\backslash\\lambda$ & "
                + " & ".join(f"{x:g}" for x in WEIGHT_GRID)
                + " \\\\\n\\midrule\n")
        for pi in WEIGHT_GRID:
            cells = [f"{winners[(pi, lam)][0]} "
                     f"({winners[(pi, lam)][1]:.1f})"
                     for lam in WEIGHT_GRID]
            f.write(f"{pi:g} & " + " & ".join(cells) + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(here, "..", "data")
    os.makedirs(out_dir, exist_ok=True)

    rows = []
    t0 = time.time()
    # main factorial
    for profile in ("sparse", "dense"):
        for cls in CLASSES:
            for p in LEVELS:
                for seed in SEEDS:
                    rows.append(run_condition(cls, p, seed, profile))
            print(f"[{time.time()-t0:6.1f}s] main {profile}/{cls}")
    # sensitivity arms (dense unless stated), p sweep on the affected class
    for p in LEVELS:
        for seed in SEEDS:
            rows.append(run_condition("correlation_ids", p, seed, "dense",
                                      window_h=24.0, tag="window24"))
            rows.append(run_condition("correlation_ids", p, seed, "dense",
                                      redundancy=False, tag="noredund"))
            rows.append(run_condition("intent_links", p, seed, "dense",
                                      filer_mismatch=0.30, tag="filer30"))
    print(f"[{time.time()-t0:6.1f}s] sensitivity sweeps")
    # single-knob density sweep, combined arm at p=0.10
    for prof in ("mid1", "mid2", "mid3"):
        for seed in SEEDS:
            rows.append(run_condition("combined", 0.10, seed, prof,
                                      tag="densweep"))
    print(f"[{time.time()-t0:6.1f}s] density sweep")

    path_rows = []
    for profile in ("sparse", "dense"):
        for p in LEVELS:
            for seed in SEEDS:
                path_rows.append(run_pairwise_path_diagnostic(p, seed, profile))
    with open(os.path.join(out_dir, "pairwise_path_diagnostic.csv"), "w",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(path_rows[0].keys()),
                           lineterminator="\n")
        w.writeheader()
        w.writerows(path_rows)
    path_agg = agg_rows(path_rows, ["profile", "p"])
    with open(os.path.join(out_dir, "pairwise_path_summary.csv"), "w",
              newline="") as f:
        fields_path = ["premise_rate", "only_union_loss_rate",
                       "conditional_loss"]
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["profile", "p"] +
                   [item for field in fields_path
                    for item in (field, field + "_sd")])
        for key, group in sorted(path_agg.items()):
            row = list(key)
            for field in fields_path:
                row.extend(mean_sd(group, field))
            w.writerow(row)
    print(f"[{time.time()-t0:6.1f}s] paired path diagnostic")

    with open(os.path.join(out_dir, "results_raw.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()),
                           lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    fields = ["coverage", "false_rate", "chain_cov", "recloss", "irrec",
              "error_links", "irrec_links", "no_cert_links", "fallback",
              "candidates", "ed_effort", "ed_error", "ed_abstention", "ed",
              "secs"]
    agg = agg_rows(rows, ["tag", "profile", "cls", "p"])
    with open(os.path.join(out_dir, "results.csv"), "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        header = ["tag", "profile", "cls", "p"]
        for k in fields:
            header += [k, k + "_sd"]
        w.writerow(header)
        for key, rs in sorted(agg.items()):
            row = list(key)
            for k in fields:
                m, s = mean_sd(rs, k)
                row += [m, s]
            w.writerow(row)

    write_pi_sensitivity(agg, out_dir)
    write_weight_sensitivity(agg, out_dir)

    # series files for pgfplots (main runs only)
    ser_dir = os.path.join(out_dir, "series")
    os.makedirs(ser_dir, exist_ok=True)
    base = {}
    for key, rs in agg.items():
        tag, profile, cls, p = key
        if tag == "main" and p == 0.0:
            base[(profile, cls)] = mean_sd(rs, "candidates")[0] or 1.0
    series = {}
    for key, rs in sorted(agg.items()):
        tag, profile, cls, p = key
        if tag != "main":
            continue
        m = {k: mean_sd(rs, k)[0] for k in fields}
        s = {k: mean_sd(rs, k)[1] for k in fields}
        fb = m["fallback"]
        series.setdefault((profile, cls), []).append(
            (p * 100, m["coverage"], s["coverage"], m["false_rate"],
             s["false_rate"], m["recloss"], s["recloss"], m["irrec"],
             s["irrec"], fb, m["candidates"], m["ed"], m["ed_effort"],
             m["ed_error"], m["ed_abstention"]))
    for (profile, cls), pts in series.items():
        with open(os.path.join(ser_dir, f"{profile}_{cls}.csv"), "w",
                  newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["p", "cov", "covsd", "false", "falsesd", "recloss",
                        "reclosssd", "irrec", "irrecsd", "fallback",
                        "candidates", "ed", "ed_effort", "ed_error",
                        "ed_abstention"])
            for pt in sorted(pts):
                w.writerow(pt)

    with open(os.path.join(out_dir, "interest.csv"), "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["day", "attempt_cost", "p_error", "p_irrec", "burden"])
        for row in interest_curve():
            w.writerow(row)

    # programmatic LaTeX table rows (guards against transcription error)
    def fmt(key, k, dec=3):
        m, s = mean_sd(agg[key], k)
        return f"{m:.{dec}f} ({s:.{dec}f})"
    sel = [
        ("main", "sparse", "combined", 0.0), ("main", "dense", "combined", 0.0),
        ("main", "dense", "intent_links", 0.4),
        ("main", "dense", "approval_links", 0.4),
        ("main", "dense", "correlation_ids", 0.4),
        ("main", "dense", "timestamps", 0.4),
        ("main", "dense", "ids_plus_timestamps", 0.4),
        ("main", "sparse", "source_artifacts", 0.4),
        ("main", "dense", "source_artifacts", 0.4),
        ("main", "sparse", "combined", 0.05), ("main", "dense", "combined", 0.05),
        ("main", "sparse", "combined", 0.2), ("main", "dense", "combined", 0.2),
        ("main", "sparse", "combined", 0.4), ("main", "dense", "combined", 0.4),
    ]
    header = ("\\begin{tabular}{@{}llrccccccc@{}}\n\\toprule\n"
              "\\textbf{Class} & \\textbf{Prof.} & $p$ & $S$ & $W$ & $N$ & "
              "\\textbf{FRR} & \\textbf{IRR$_{ch}$} & \\textbf{ERC} & "
              "$\\ED_\\rho$ \\\\\n\\midrule\n")
    body = []
    with open(os.path.join(out_dir, "table_rows.tex"), "w") as f:
        for key in sel:
            tag, profile, cls, p = key
            name = cls.replace("_", " ")
            line = (f"{name} & {profile} & {int(p*100)}\\% & "
                    f"{mean_sd(agg[key],'coverage')[0]:.3f} & "
                    f"{mean_sd(agg[key],'error_links')[0]:.3f} & "
                    f"{mean_sd(agg[key],'no_cert_links')[0]:.3f} & "
                    f"{mean_sd(agg[key],'false_rate')[0]:.3f} & "
                    f"{mean_sd(agg[key],'irrec')[0]:.3f} & "
                    f"{mean_sd(agg[key],'ed_effort')[0]:.1f} & "
                    f"{mean_sd(agg[key],'ed')[0]:.1f} \\\\\n")
            f.write(line)
            body.append(line)
    with open(os.path.join(out_dir, "table_full.tex"), "w") as f:
        f.write(header + "".join(body) + "\\bottomrule\n\\end{tabular}\n")
    print("wrote results.csv, results_raw.csv, series/, interest.csv, "
          "pairwise path diagnostics, table_rows.tex, pi_sensitivity.csv, "
          "table_pi_sensitivity.tex, table_pi_sensitivity_compact.tex, "
          "weight_sensitivity.csv, and "
          "table_weight_sensitivity.tex")


if __name__ == "__main__":
    main()
