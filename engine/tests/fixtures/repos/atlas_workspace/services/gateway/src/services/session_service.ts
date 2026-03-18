export class SessionService {
  generateRefreshToken(sessionSubject: string): string {
    return `refresh::${sessionSubject}`;
  }

  rotateRefreshToken(refreshToken: string) {
    const subject = refreshToken.replace("refresh::", "");
    return {
      refreshToken: this.generateRefreshToken(subject),
      accessToken: `bearer::${subject}`,
    };
  }
}
