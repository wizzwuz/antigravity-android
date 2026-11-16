"""Eligibility and voice gate patch.

Strategy (adaptive, signature based, no fixed offsets):

  1. CLI gate   : `ldrb w1, [x0, #8]` (01 20 40 39) followed by `tbnz w1, #0, ...`
                  -> replace the load with `mov w1, #1` (21 00 80 52).
  2. Manager auth: `authclient.(*EnterpriseAuthValidator).Validate` gate
                  : `ldrb w3, [x0, #8]` (03 20 40 39) + `tbz w3, #0, ...`
                    + token setup
                  -> replace load+test with `mov w3, #1 ; strb w3, [x0, #8]`
                     (23 00 80 52 03 20 00 39).
  3. Voice gates : `(*Server).isVoiceRelayEnabled` and `(*Server).isVoiceAllowedIn`
                  -> NOP out conditional branches before `orr x0, xzr, #1 ; ret`.

Fail-closed: the number of raw + already-patched sites must equal the
expected counts (cli=2, manager=1, voice_relay=1, voice_allowed=1).
"""

import sys

from patch_lib import cli as _cli
from patch_lib import module_base as base
from patch_lib.report import hex_list
from groups.gates import signatures as sig
from groups.gates.analyze import analyze

GROUP_ID = "eligibility"
GROUP = "eligibility"
FILE = "gates"
DESCRIPTION = "Force eligibility/auth/voice gate bits (CLI + EnterpriseAuthValidator + VoiceRelay)."
EXPECTED_COUNTS = {
    "cli": 2,
    "manager": 1,
    "voice_relay": 1,
    "voice_allowed": 1,
    "voice_cfg_s1": 1,
    "voice_cfg_s2": 1,
    "sbox_avail": 1,
    "sbox_init": 1,
    "sbox_prep": 1,
}
TAG = "patch_gates"


def run(target_path, verify=False, dry_run=False, allow_missing=False, log=print):
    """Apply / check the eligibility gate patch. Returns (ok, report)."""
    report = base.new_report(
        GROUP_ID, GROUP, FILE, DESCRIPTION,
        expected_counts=EXPECTED_COUNTS, offsets={})

    data = base.read_target(target_path, report)
    if data is None:
        return False, report

    st = analyze(data)
    summary = {
        "cli": len(st["raw_cli"]) + len(st["pat_cli"]),
        "manager": len(st["raw_mgr"]) + len(st["pat_mgr"]),
        "voice_relay": len(st["raw_vrel"]) + len(st["pat_vrel"]),
        "voice_allowed": len(st["raw_vall"]) + len(st["pat_vall"]),
        "voice_cfg_s1": len(st["raw_vc1"]) + len(st["pat_vc1"]),
        "voice_cfg_s2": len(st["raw_vc2"]) + len(st["pat_vc2"]),
        "sbox_avail": len(st["raw_sbox_avail"]) + len(st["pat_sbox_avail"]),
        "sbox_init": len(st["raw_sbox_init"]) + len(st["pat_sbox_init"]),
        "sbox_prep": len(st["raw_sbox_prep"]) + len(st["pat_sbox_prep"]),
    }
    report["observed_counts"] = {
        "cli": {"raw": len(st["raw_cli"]), "patched": len(st["pat_cli"])},
        "manager": {"raw": len(st["raw_mgr"]), "patched": len(st["pat_mgr"])},
        "voice_relay": {"raw": len(st["raw_vrel"]), "patched": len(st["pat_vrel"])},
        "voice_allowed": {"raw": len(st["raw_vall"]), "patched": len(st["pat_vall"])},
        "voice_cfg_s1": {"raw": len(st["raw_vc1"]), "patched": len(st["pat_vc1"])},
        "voice_cfg_s2": {"raw": len(st["raw_vc2"]), "patched": len(st["pat_vc2"])},
        "sbox_avail": {"raw": len(st["raw_sbox_avail"]), "patched": len(st["pat_sbox_avail"])},
        "sbox_init": {"raw": len(st["raw_sbox_init"]), "patched": len(st["pat_sbox_init"])},
        "sbox_prep": {"raw": len(st["raw_sbox_prep"]), "patched": len(st["pat_sbox_prep"])},
    }
    report["offsets"] = {
        "cli_raw": hex_list(st["raw_cli"]),
        "cli_patched": hex_list(st["pat_cli"]),
        "manager_raw": hex_list(st["raw_mgr"]),
        "manager_patched": hex_list(st["pat_mgr"]),
        "voice_relay_raw": hex_list(st["raw_vrel"]),
        "voice_relay_patched": hex_list(st["pat_vrel"]),
        "voice_allowed_raw": hex_list(st["raw_vall"]),
        "voice_allowed_patched": hex_list(st["pat_vall"]),
        "voice_cfg_s1_raw": hex_list(st["raw_vc1"]),
        "voice_cfg_s1_patched": hex_list(st["pat_vc1"]),
        "voice_cfg_s2_raw": hex_list(st["raw_vc2"]),
        "voice_cfg_s2_patched": hex_list(st["pat_vc2"]),
        "sbox_avail_raw": hex_list(st["raw_sbox_avail"]),
        "sbox_avail_patched": hex_list(st["pat_sbox_avail"]),
        "sbox_init_raw": hex_list(st["raw_sbox_init"]),
        "sbox_init_patched": hex_list(st["pat_sbox_init"]),
        "sbox_prep_raw": hex_list(st["raw_sbox_prep"]),
        "sbox_prep_patched": hex_list(st["pat_sbox_prep"]),
    }

    for shape in ("cli", "manager", "voice_relay", "voice_allowed", "voice_cfg_s1", "voice_cfg_s2", "sbox_avail", "sbox_init", "sbox_prep"):
        total = summary[shape]
        exp = EXPECTED_COUNTS[shape]
        if total == 0:
            if shape == "voice_cfg_s2" or allow_missing:
                report["observed_counts"][shape] = {"raw": 0, "patched": 0}
                continue
            msg = "missing %s gate signature (expected %d)" % (shape, exp)
            if not base.run_missing(report, allow_missing, TAG, log, msg):
                return False, report
        elif total != exp:
            report["messages"].append(
                "unexpected %s gate count %d (expected %d)" % (shape, total, exp)
            )
            log("[patch_gates] ERROR: %s" % report["messages"][-1])
            return False, report

    if verify:
        has_vc2 = summary["voice_cfg_s2"] > 0
        ok = (
            len(st["raw_cli"]) == 0
            and len(st["pat_cli"]) == EXPECTED_COUNTS["cli"]
            and len(st["raw_mgr"]) == 0
            and len(st["pat_mgr"]) == EXPECTED_COUNTS["manager"]
            and len(st["raw_vrel"]) == 0
            and len(st["pat_vrel"]) == EXPECTED_COUNTS["voice_relay"]
            and len(st["raw_vall"]) == 0
            and len(st["pat_vall"]) == EXPECTED_COUNTS["voice_allowed"]
            and len(st["raw_vc1"]) == 0
            and len(st["pat_vc1"]) == EXPECTED_COUNTS["voice_cfg_s1"]
            and (not has_vc2 or (len(st["raw_vc2"]) == 0 and len(st["pat_vc2"]) == EXPECTED_COUNTS["voice_cfg_s2"]))
            and len(st["raw_sbox_avail"]) == 0
            and len(st["pat_sbox_avail"]) == EXPECTED_COUNTS["sbox_avail"]
            and len(st["raw_sbox_init"]) == 0
            and len(st["pat_sbox_init"]) == EXPECTED_COUNTS["sbox_init"]
            and len(st["raw_sbox_prep"]) == 0
            and len(st["pat_sbox_prep"]) == EXPECTED_COUNTS["sbox_prep"]
        )
        return base.run_verify(report, ok, TAG, log), report

    n_changes = (
        len(st["raw_cli"])
        + len(st["raw_mgr"])
        + len(st["raw_vrel"])
        + len(st["raw_vall"])
        + len(st["raw_vc1"])
        + len(st["raw_vc2"])
        + len(st["raw_sbox_avail"])
        + len(st["raw_sbox_init"])
        + len(st["raw_sbox_prep"])
    )
    if n_changes == 0:
        return base.run_already(
            report, TAG, log,
            message="already patched, nothing to do",
            log_message="already patched",
            detail=" (cli=%d, manager=%d, vrel=%d, vall=%d, vc1=%d, vc2=%d, sbox=%d/%d/%d)" %
            (len(st["pat_cli"]), len(st["pat_mgr"]), len(st["pat_vrel"]), len(st["pat_vall"]), len(st["pat_vc1"]), len(st["pat_vc2"]), len(st["pat_sbox_avail"]), len(st["pat_sbox_init"]), len(st["pat_sbox_prep"]))), report

    for off in st["raw_cli"]:
        data[off:off + 4] = sig.REPL_CLI
    for off in st["raw_mgr"]:
        data[off:off + 8] = sig.REPL_MGR
    for off in st["raw_vrel"]:
        data[off:off + len(sig.REPL_VOICE_RELAY)] = sig.REPL_VOICE_RELAY
    for off in st["raw_vall"]:
        data[off:off + len(sig.REPL_VOICE_ALLOWED)] = sig.REPL_VOICE_ALLOWED
    for off in st["raw_vc1"]:
        data[off:off + len(sig.REPL_VOICE_CFG_S1)] = sig.REPL_VOICE_CFG_S1
    for off in st["raw_vc2"]:
        data[off:off + len(sig.REPL_VOICE_CFG_S2)] = sig.REPL_VOICE_CFG_S2
    for off in st["raw_sbox_avail"]:
        data[off:off + len(sig.REPL_SBOX_AVAIL)] = sig.REPL_SBOX_AVAIL
    for off in st["raw_sbox_init"]:
        data[off:off + len(sig.REPL_SBOX_INIT)] = sig.REPL_SBOX_INIT
    for off in st["raw_sbox_prep"]:
        data[off:off + len(sig.REPL_SBOX_PREP)] = sig.REPL_SBOX_PREP

    report["state"] = "dry-run" if dry_run else "patched"
    report["changed"] = n_changes
    report["messages"].append("would patch" if dry_run else "patched")
    if dry_run:
        log("[patch_gates] dry-run: %d site(s) would be patched" % n_changes)
        return True, report

    base.commit_write(
        target_path, data, log, TAG,
        "patched cli=%d manager=%d vrel=%d vall=%d vc1=%d vc2=%d sbox=%d/%d/%d" % (
            len(st["raw_cli"]), len(st["raw_mgr"]), len(st["raw_vrel"]), len(st["raw_vall"]), len(st["raw_vc1"]), len(st["raw_vc2"]), len(st["raw_sbox_avail"]), len(st["raw_sbox_init"]), len(st["raw_sbox_prep"])))
    return True, report


if __name__ == "__main__":
    sys.exit(_cli.main(run))
