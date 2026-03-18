package com.atlas.session;

import java.time.Instant;

public class SessionExpiryManager {
    public boolean handleSessionExpiration(SessionRecord session, Instant now) {
        return session.expiresAt().isBefore(now) || session.expiresAt().equals(now);
    }
}
