use vstd::prelude::*;

fn main() {}

verus! {

pub struct Request {
    pub caller: u64,
    pub capability_id: u64,
    pub resource: u64,
    pub action: u64,
}

// The type is visible so trusted host code can hold it, but its authority-bearing
// fields are private. A third-party worker is expected to be outside this crate
// and, in the intended architecture, outside this process.
pub struct KernelState {
    constitution_allows: bool,
    site_policy_allows: bool,
    grant_present: bool,
    grant_id: u64,
    grant_subject: u64,
    grant_resource: u64,
    grant_action: u64,
    grant_epoch: u64,
    current_epoch: u64,
}

impl KernelState {
    // Public callers may name this predicate but cannot unfold it outside the
    // module. The authority-bearing representation remains opaque.
    pub closed spec fn request_authorized(&self, req: &Request) -> bool {
        self.constitution_allows
            && self.site_policy_allows
            && self.grant_present
            && self.current_epoch > 0
            && self.grant_epoch == self.current_epoch
            && req.capability_id == self.grant_id
            && req.caller == self.grant_subject
            && req.resource == self.grant_resource
            && req.action == self.grant_action
    }

    // TRUSTED_BOOTSTRAP: this is deliberately not public outside the crate.
    // In a production design, creation/mutation of KernelState belongs to the
    // trusted Authority Core, never to a third-party worker.
    pub(crate) fn bootstrap(
        constitution_allows: bool,
        site_policy_allows: bool,
        grant_present: bool,
        grant_id: u64,
        grant_subject: u64,
        grant_resource: u64,
        grant_action: u64,
        grant_epoch: u64,
        current_epoch: u64,
    ) -> (state: Self)
        ensures
            state.constitution_allows == constitution_allows,
            state.site_policy_allows == site_policy_allows,
            state.grant_present == grant_present,
            state.grant_id == grant_id,
            state.grant_subject == grant_subject,
            state.grant_resource == grant_resource,
            state.grant_action == grant_action,
            state.grant_epoch == grant_epoch,
            state.current_epoch == current_epoch,
    {
        KernelState {
            constitution_allows,
            site_policy_allows,
            grant_present,
            grant_id,
            grant_subject,
            grant_resource,
            grant_action,
            grant_epoch,
            current_epoch,
        }
    }

    // UNTRUSTED_BOUNDARY_V1: no verifier-only caller precondition is allowed.
    // The hostile caller supplies only Request. Constitutional policy, site
    // policy, issued grant data and revocation epoch come from opaque private state.
    pub fn authorize_request(&self, req: &Request) -> (allowed: bool)
        ensures
            allowed == self.request_authorized(req),
    {
        self.constitution_allows
            && self.site_policy_allows
            && self.grant_present
            && self.current_epoch > 0
            && self.grant_epoch == self.current_epoch
            && req.capability_id == self.grant_id
            && req.caller == self.grant_subject
            && req.resource == self.grant_resource
            && req.action == self.grant_action
    }
}

// The following internal theorems connect the opaque public authorization
// predicate to the constitutional properties. They may inspect private state;
// untrusted callers cannot manufacture those state facts through Request.
proof fn constitutional_denial_cannot_be_amplified(state: KernelState, req: Request)
    requires
        !state.constitution_allows,
    ensures
        !state.request_authorized(&req),
{
}

proof fn forged_capability_id_is_denied(state: KernelState, req: Request)
    requires
        req.capability_id != state.grant_id,
    ensures
        !state.request_authorized(&req),
{
}

proof fn cross_subject_use_is_denied(state: KernelState, req: Request)
    requires
        req.caller != state.grant_subject,
    ensures
        !state.request_authorized(&req),
{
}

proof fn cross_resource_use_is_denied(state: KernelState, req: Request)
    requires
        req.resource != state.grant_resource,
    ensures
        !state.request_authorized(&req),
{
}

proof fn cross_action_use_is_denied(state: KernelState, req: Request)
    requires
        req.action != state.grant_action,
    ensures
        !state.request_authorized(&req),
{
}

proof fn stale_grant_is_denied(state: KernelState, req: Request)
    requires
        state.grant_epoch != state.current_epoch,
    ensures
        !state.request_authorized(&req),
{
}

} // verus!
