package com.mithaq.app.probe;

/** Internal Phase-0 diagnostic contract; not exported to third-party packages. */
interface IIsolatedInferenceProbe {
    int getWorkerUid();
    boolean canReadPath(String path);
    int checkInternetPermission();
}
