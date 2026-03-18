import { SessionService } from "../services/session_service";
import { TokenVerifier } from "../security/token_verifier";

export class AuthController {
  constructor(
    private readonly sessions: SessionService,
    private readonly verifier: TokenVerifier
  ) {}

  loginWithPassword(username: string, password: string, preflightToken?: string) {
    if (!username || !password) {
      throw new Error("missing credentials");
    }
    if (preflightToken) {
      this.verifier.enforceTokenValidation(preflightToken);
    }
    const refreshToken = this.sessions.generateRefreshToken(username);
    return { refreshToken, tokenType: "bearer" };
  }

  refreshSession(refreshToken: string) {
    return this.sessions.rotateRefreshToken(refreshToken);
  }
}
