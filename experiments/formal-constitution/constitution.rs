// V0_PEDAGOGICAL_COUNTEREXAMPLE
//
// This file is intentionally retained as a mechanically verified but
// specification-insufficient model. It demonstrates that a green proof is not
// enough when authority facts themselves are supplied by an attacker. Do not
// use this file as the candidate PolaCore authorization boundary. The corrected
// trusted-state direction is `capability_kernel.rs`.

use vstd::prelude::*;

fn main() {}

verus! {

spec fn constitutional_allow(
    constitution: bool,
    site_policy: bool,
    capability_present: bool,
    capability_epoch: u64,
    current_epoch: u64,
) -> bool {
    constitution
        && site_policy
        && capability_present
        && capability_epoch == current_epoch
        && current_epoch > 0
}

spec fn state_invariant(admin: bool, current_epoch: u64) -> bool {
    admin ==> current_epoch > 0
}

// UNTRUSTED_BOUNDARY: this v0 boundary intentionally accepts all authority
// facts from the caller. Verus proves the stated relation, but that relation is
// too weak for a hostile PolaCore boundary because the caller can assert that
// constitutional/capability authority exists.
fn authorize(
    constitution: bool,
    site_policy: bool,
    capability_present: bool,
    capability_epoch: u64,
    current_epoch: u64,
) -> (allowed: bool)
    ensures
        allowed == constitutional_allow(
            constitution,
            site_policy,
            capability_present,
            capability_epoch,
            current_epoch,
        ),
        allowed ==> constitution,
        allowed ==> site_policy,
        allowed ==> capability_present,
        allowed ==> capability_epoch == current_epoch,
        allowed ==> current_epoch > 0,
{
    constitution
        && site_policy
        && capability_present
        && capability_epoch == current_epoch
        && current_epoch > 0
}

// UNTRUSTED_BOUNDARY: retained to show why proving one mediated path does not
// establish whole-system complete mediation when its authority facts are hostile.
fn mediate_admin_transition(
    admin_before: bool,
    wants_admin: bool,
    constitution: bool,
    site_policy: bool,
    capability_present: bool,
    capability_epoch: u64,
    current_epoch: u64,
) -> (admin_after: bool)
    ensures
        state_invariant(admin_before, current_epoch)
            ==> state_invariant(admin_after, current_epoch),
        admin_after && !admin_before
            ==> constitutional_allow(
                constitution,
                site_policy,
                capability_present,
                capability_epoch,
                current_epoch,
            ),
        !admin_before && !constitution ==> !admin_after,
        !admin_before && !site_policy ==> !admin_after,
        !admin_before && !capability_present ==> !admin_after,
        !admin_before && capability_epoch != current_epoch ==> !admin_after,
{
    let allowed = authorize(
        constitution,
        site_policy,
        capability_present,
        capability_epoch,
        current_epoch,
    );

    if admin_before {
        true
    } else if wants_admin && allowed {
        true
    } else {
        false
    }
}

proof fn constitution_is_supreme(
    constitution: bool,
    site_policy: bool,
    capability_present: bool,
    capability_epoch: u64,
    current_epoch: u64,
)
    ensures
        constitutional_allow(
            constitution,
            site_policy,
            capability_present,
            capability_epoch,
            current_epoch,
        ) ==> constitution,
{
}

proof fn local_policy_cannot_amplify_denied_constitution(
    site_policy: bool,
    capability_present: bool,
    capability_epoch: u64,
    current_epoch: u64,
)
    ensures
        !constitutional_allow(
            false,
            site_policy,
            capability_present,
            capability_epoch,
            current_epoch,
        ),
{
}

proof fn stale_capability_is_denied(
    constitution: bool,
    site_policy: bool,
    capability_present: bool,
    capability_epoch: u64,
    current_epoch: u64,
)
    requires
        capability_epoch != current_epoch,
    ensures
        !constitutional_allow(
            constitution,
            site_policy,
            capability_present,
            capability_epoch,
            current_epoch,
        ),
{
}

} // verus!
