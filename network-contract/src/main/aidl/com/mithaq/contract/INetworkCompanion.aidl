package com.mithaq.contract;

/**
 * Narrow Phase-0 Binder contract.
 * This is deliberately not a generic HTTP proxy or arbitrary URL interface.
 */
interface INetworkCompanion {
    int getProtocolVersion();
    int getServiceUid();
    String echoChallenge(String challenge);
}
