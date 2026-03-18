import { SessionClaims, TokenVerifier } from "./token_verifier";

export class CurrentPrincipalResolver {
  constructor(private readonly verifier: TokenVerifier) {}

  resolve(accessToken: string): SessionClaims {
    return this.verifier.enforceTokenValidation(accessToken);
  }
}
