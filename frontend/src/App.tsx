import { useCallback, useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate, useSearchParams } from "react-router-dom";

import { api, UNAUTHENTICATED_EVENT } from "./api";
import arenaLogo from "./assets/arena-cat-logo.svg";
import logotip from "./assets/softcatala-logotip.png";
import AccountMenu from "./components/AccountMenu";
import ActivityView from "./components/ActivityView";
import DeleteAccountDialog from "./components/DeleteAccountDialog";
import ForgotPasswordView from "./components/ForgotPasswordView";
import HowItWorksView from "./components/HowItWorksView";
import Login from "./components/Login";
import QualificationView from "./components/QualificationView";
import ReminderView from "./components/ReminderView";
import RankingView from "./components/RankingView";
import ResetPasswordView from "./components/ResetPasswordView";
import TaskView from "./components/TaskView";
import VerifyView from "./components/VerifyView";
import { clearTask } from "./taskStore";
import type { Category, SessionState } from "./types";

const UNKNOWN: SessionState = {
  authenticated: false,
  email: null,
  email_verified: false,
  qualified: false,
};

export default function App() {
  // `null` mentre no sabem si hi ha sessió: sense aquest estat intermedi
  // ensenyaríem el formulari un instant a qui ja té la sessió oberta.
  const [session, setSession] = useState<SessionState | null>(null);
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [categoriesError, setCategoriesError] = useState(false);
  const [showDeleteAccount, setShowDeleteAccount] = useState(false);
  const [accountDeleted, setAccountDeleted] = useState(false);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const debugQuery = searchParams.has("debug") ? "?debug" : "";

  const refresh = useCallback(async () => {
    try {
      setSession(await api.session());
      setAccountDeleted(false);
    } catch {
      // Backend inaccessible: el tractem com a no autenticat, però l'error de
      // connexió ja el mostrarà el formulari quan s'intenti entrar.
      setSession(UNKNOWN);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const refreshCategories = useCallback(async () => {
    setCategoriesError(false);
    try {
      setCategories(await api.categories());
    } catch {
      setCategories(null);
      setCategoriesError(true);
    }
  }, []);

  useEffect(() => {
    void refreshCategories();
  }, [refreshCategories]);

  // La tasca en curs pertany a la sessió: quan s'acaba, s'ha de descartar. Si no,
  // en tornar a entrar es restauraria amb el `vote_after` ja vençut (i per tant
  // sense compte enrere), i si hi entrés una altra persona veuria una tasca que
  // no és seva i que el backend li rebutjaria amb un 403.
  useEffect(() => {
    const onUnauthenticated = () => {
      clearTask();
      setShowDeleteAccount(false);
      setSession(UNKNOWN);
    };
    window.addEventListener(UNAUTHENTICATED_EVENT, onUnauthenticated);
    return () => window.removeEventListener(UNAUTHENTICATED_EVENT, onUnauthenticated);
  }, []);

  function logout() {
    clearTask();
    void api.logout().finally(() => {
      setSession(UNKNOWN);
      navigate("/login");
    });
  }

  return (
    // El coixí inferior va aquí i no dins de TaskView perquè la barra de vot, que al
    // mòbil és fixada, tapa el final del document — i el final del document és el peu.
    <div className="min-h-screen bg-slate-50 pb-44 text-slate-900 md:pb-0">
      <header className="border-b-4 border-brand-500 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <Link
            to="/"
            className="flex items-center gap-3 rounded focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:outline-none"
          >
            <img src={arenaLogo} alt="" width={44} height={44} className="h-11 w-11" />
            <span>
              <span className="block text-lg font-bold text-brand-600">Arena Cat</span>
              <span className="block text-sm text-slate-500">
                Avaluació humana de models d'IA en català
              </span>
            </span>
          </Link>
          <div className="ml-auto flex items-center gap-2">
            <Link to="/ranking" className="text-sm text-brand-600 hover:underline">
              Rànquing
            </Link>
            {session?.authenticated && (
              <AccountMenu
                email={session.email}
                onLogout={logout}
                onDeleteAccount={() => setShowDeleteAccount(true)}
              />
            )}
          </div>
        </div>
      </header>

      <div className="border-b border-slate-200 bg-slate-50 text-slate-900">
        <div className="mx-auto flex max-w-5xl items-start gap-3 px-4 py-3">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="mt-0.5 h-5 w-5 shrink-0 text-slate-600"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="9" />
            <path d="M12 11v6M12 7h.01" />
          </svg>
          <div>
            <p className="text-base font-semibold">Necessiteu ajuda?</p>
            <p className="mt-1 text-sm">
              Si necessiteu ajuda, hi trobeu errades o voleu proposar millores, podeu anar al{" "}
              <a
                href="https://t.me/+dAgCZcRS2R82OGI0"
                className="font-semibold underline underline-offset-2 hover:no-underline"
              >
                grup de Telegram
              </a>
              .
            </p>
          </div>
        </div>
      </div>

      {session?.authenticated && showDeleteAccount && (
        <DeleteAccountDialog
          onClose={() => setShowDeleteAccount(false)}
          onDeleted={() => {
            clearTask();
            setShowDeleteAccount(false);
            setSession(UNKNOWN);
            setAccountDeleted(true);
            navigate("/");
          }}
        />
      )}

      <main>
        {accountDeleted && (
          <p role="status" className="mx-auto max-w-5xl px-4 pt-4 text-brand-700">
            El compte s'ha donat de baixa.
          </p>
        )}
        {session === null ? (
          <p className="px-4 py-10 text-center text-slate-500">Carregant…</p>
        ) : (
          <Routes>
            <Route
              path="/reminders"
              element={
                session.authenticated ? (
                  <ReminderView key="preferences" />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />
            <Route
              path="/reminders/unsubscribe"
              element={<ReminderView key="unsubscribe" unsubscribe />}
            />
            <Route
              path="/ranking"
              element={
                categories ? (
                  <RankingView
                    categories={categories}
                    authenticated={session.authenticated}
                    onEvaluate={() => navigate(session.authenticated ? "/" : `/login${debugQuery}`)}
                  />
                ) : (
                  <CategoriesStatus error={categoriesError} onRetry={refreshCategories} />
                )
              }
            />
            <Route
              path="/activitat"
              element={session.authenticated ? <ActivityView /> : <Navigate to="/login" replace />}
            />
            <Route path="/com-funciona" element={<HowItWorksView />} />
            <Route
              path="/login"
              element={
                session.authenticated ? (
                  <Navigate to={`/${debugQuery}`} replace />
                ) : (
                  <Login onLoggedIn={refresh} />
                )
              }
            />
            {/* Obert a tothom: qui rep el correu encara no té sessió, i qui en té una
                també pot obrir l'enllaç. */}
            <Route path="/verify" element={<VerifyView />} />
            <Route
              path="/forgot-password"
              element={session.authenticated ? <Navigate to="/" replace /> : <ForgotPasswordView />}
            />
            {/* Obert a tothom, com /verify: qui ha perdut la contrasenya no té sessió. */}
            <Route path="/reset-password" element={<ResetPasswordView />} />
            <Route
              path="/qualification"
              element={
                !session.authenticated ? (
                  <Navigate to={`/login${debugQuery}`} replace />
                ) : session.qualified ? (
                  <Navigate to="/" replace />
                ) : categories ? (
                  <QualificationView categories={categories} onContinue={refresh} />
                ) : (
                  <CategoriesStatus error={categoriesError} onRetry={refreshCategories} />
                )
              }
            />
            <Route
              path="/"
              element={
                session.authenticated ? (
                  !session.qualified ? (
                    <Navigate to={`/qualification${debugQuery}`} replace />
                  ) : categories ? (
                    <TaskView categories={categories} />
                  ) : (
                    <CategoriesStatus error={categoriesError} onRetry={refreshCategories} />
                  )
                ) : categories ? (
                  <RankingView
                    categories={categories}
                    onEvaluate={() => navigate(`/login${debugQuery}`)}
                  />
                ) : (
                  <CategoriesStatus error={categoriesError} onRetry={refreshCategories} />
                )
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        )}
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-col items-center gap-2 px-4 py-6">
          <span className="text-sm text-slate-500">Un projecte de</span>
          {/* El logotip és el nom escrit, així que l'`alt` és el nom i no el
              repetim al costat. `width`/`height` eviten que el peu salti mentre
              la imatge es carrega. */}
          <a
            href="https://www.softcatala.org"
            target="_blank"
            rel="noreferrer"
            className="rounded focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:outline-none"
          >
            <img src={logotip} alt="Softcatalà" width={146} height={90} className="h-14 w-auto" />
          </a>
        </div>
      </footer>
    </div>
  );
}

function CategoriesStatus({ error, onRetry }: { error: boolean; onRetry: () => void }) {
  return (
    <div className="px-4 py-10 text-center text-slate-500">
      {error ? (
        <>
          <p role="alert">No s'han pogut carregar les categories.</p>
          <button type="button" onClick={onRetry} className="mt-3 underline hover:text-brand-600">
            Torna-ho a provar
          </button>
        </>
      ) : (
        <p>Carregant categories…</p>
      )}
    </div>
  );
}
