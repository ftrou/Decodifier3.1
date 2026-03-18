export class PermissionGate {
  assertPermission(scopes: string[], requiredScope: string): void {
    if (!this.hasScope(scopes, requiredScope)) {
      throw new Error(`missing ${requiredScope}`);
    }
  }

  hasScope(scopes: string[], requiredScope: string): boolean {
    return scopes.includes(requiredScope);
  }
}
