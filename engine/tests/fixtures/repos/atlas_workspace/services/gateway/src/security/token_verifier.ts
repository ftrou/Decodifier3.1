export interface SessionClaims {
  subject: string;
  scopes: string[];
  status: "active" | "expired";
}

export class TokenVerifier {
  enforceTokenValidation(token: string): SessionClaims {
    const claims = this.verifyAccessToken(token);
    if (claims.status !== "active") {
      throw new Error("token validation failed");
    }
    return claims;
  }

  verifyAccessToken(token: string): SessionClaims {
    const subject = token.replace("bearer::", "");
    return {
      subject,
      scopes: ["team:read", "billing:read"],
      status: subject.endsWith("-expired") ? "expired" : "active",
    };
  }
}
