export class AuthClient {
  validateTokenRecord(token: string): boolean {
    return token.startsWith("generated::");
  }
}
