import { useCallback, useEffect, useRef, useState } from 'react';

import { API_BASE, createApiClient } from './api/client';
import { AppShell } from './components/AppShell';
import { SignIn } from './components/SignIn';
import { Drift } from './pages/Drift';
import { Evaluation } from './pages/Evaluation';
import { Settings } from './pages/Settings';
import { Targets } from './pages/Targets';
import { clearSession, loadSession, saveSession, toSession } from './state/session';
import { useMediaQuery } from './state/useMediaQuery';
import { navigate, useHashRoute } from './state/useHashRoute';
import { useTargets } from './state/useTargets';

export default function App({ makeClient = createApiClient } = {}) {
  const [session, setSession] = useState(() => loadSession());
  const sessionRef = useRef(session);
  useEffect(() => { sessionRef.current = session; }, [session]);

  const [needsSignIn, setNeedsSignIn] = useState(false);
  const [signInError, setSignInError] = useState(null);
  const [signInBusy, setSignInBusy] = useState(false);
  const [scanRefresh, setScanRefresh] = useState(0);

  const getToken = useCallback(() => sessionRef.current?.token ?? null, []);

  const clientRef = useRef(null);
  if (clientRef.current === null) {
    clientRef.current = makeClient({
      baseUrl: API_BASE,
      getToken,
      onUnauthorized: () => {
        clearSession();
        setSession(null);
        setNeedsSignIn(true);
      },
    });
  }
  const client = clientRef.current;

  const route = useHashRoute();
  const targetsState = useTargets(client);
  const navNarrow = useMediaQuery('(max-width: 600px)');

  useEffect(() => {
    if (route.page !== 'drift' || route.targetId != null) return;
    if (targetsState.loading) return;
    if (targetsState.targets.length === 0) {
      navigate({ page: 'targets' }, { replace: true });
      return;
    }
    navigate({ page: 'drift', targetId: targetsState.targets[0].id }, { replace: true });
  }, [route.page, route.targetId, targetsState.loading, targetsState.targets]);

  async function signIn(username, password) {
    setSignInBusy(true);
    setSignInError(null);
    try {
      const token = await client.login(username, password);
      const next = toSession(token);
      saveSession(next);
      setSession(next);
      setNeedsSignIn(false);
    } catch (error) {
      setSignInError(error.message);
    } finally {
      setSignInBusy(false);
    }
  }

  function signOut() {
    clearSession();
    setSession(null);
    setNeedsSignIn(false);
  }

  const mode = session
    ? { kind: 'operator', username: session.username, role: session.role }
    : { kind: 'local' };

  let page;
  if (route.page === 'targets') {
    page = (
      <Targets
        client={client}
        targets={targetsState.targets}
        loading={targetsState.loading}
        error={targetsState.error}
        onReload={targetsState.reload}
        onOpen={(id) => navigate({ page: 'drift', targetId: id })}
        onScanQueued={(queuedTarget) => {
          navigate({ page: 'drift', targetId: queuedTarget.id });
          setScanRefresh((value) => value + 1);
        }}
        onRegistered={async (registered) => {
          await targetsState.reload();
          navigate({ page: 'drift', targetId: registered.id });
        }}
        session={session}
      />
    );
  } else if (route.page === 'evaluation') {
    page = <Evaluation client={client} />;
  } else if (route.page === 'settings') {
    page = <Settings client={client} session={session} apiBase={API_BASE} />;
  } else {
    page = (
      <Drift
        key={`${route.targetId ?? 'none'}:${scanRefresh}`}
        client={client}
        targets={targetsState.targets}
        targetsLoading={targetsState.loading}
        targetsError={targetsState.error}
        targetId={route.targetId}
        onSelectTarget={(id) => navigate({ page: 'drift', targetId: id })}
        onOpenTargets={() => navigate({ page: 'targets' })}
        session={session}
      />
    );
  }

  return (
    <>
      <AppShell route={route} mode={mode} onSignOut={signOut} navNarrow={navNarrow}>
        {page}
      </AppShell>
      {needsSignIn && (
        <SignIn onSubmit={signIn} error={signInError} busy={signInBusy} />
      )}
    </>
  );
}
