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

// UNTRUSTED_BOUNDARY: this function intentionally has no `requires` clause.
// A caller may supply any values. The function must fail closed by construction.
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

// UNTRUSTED_BOUNDARY: no caller precondition is trusted here either.
// `admin_before` models trusted kernel state supplied by the kernel itself;
// all remaining values model an adversarial request/configuration surface.
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
