import { CurrentPrincipalResolver } from "../security/current_principal";
import { PermissionGate } from "../security/permission_gate";

export class TeamController {
  constructor(
    private readonly principalResolver: CurrentPrincipalResolver,
    private readonly permissionGate: PermissionGate
  ) {}

  listMembers(accessToken: string, teamId: string) {
    const principal = this.principalResolver.resolve(accessToken);
    this.permissionGate.assertPermission(principal.scopes, "team:read");
    return [{ teamId, userId: principal.subject }];
  }

  updateMemberRole(accessToken: string, teamId: string, role: string) {
    const principal = this.principalResolver.resolve(accessToken);
    this.permissionGate.assertPermission(principal.scopes, "team:write");
    return { teamId, role, actor: principal.subject };
  }
}
