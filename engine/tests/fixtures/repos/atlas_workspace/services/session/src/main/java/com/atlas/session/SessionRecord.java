package com.atlas.session;

import java.time.Instant;

public class SessionRecord {
    private final String sessionId;
    private final Instant expiresAt;

    public SessionRecord(String sessionId, Instant expiresAt) {
        this.sessionId = sessionId;
        this.expiresAt = expiresAt;
    }

    public String sessionId() {
        return sessionId;
    }

    public Instant expiresAt() {
        return expiresAt;
    }
}
