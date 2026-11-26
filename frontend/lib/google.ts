// Google's "Sign in with Google" button, from Google Identity Services (https://accounts.google.com/gsi/client).
// Only the parts the sign-in screen uses are typed here.

type GoogleButtonOptions = {
  type?: "standard" | "icon";
  theme?: "outline" | "filled_blue" | "filled_black";
  size?: "large" | "medium" | "small";
  text?: "signin_with" | "signup_with" | "continue_with" | "signin";
  shape?: "rectangular" | "pill" | "circle" | "square";
  logo_alignment?: "left" | "center";
  width?: number;
  locale?: string;
};

type GoogleIdentityServices = {
  initialize(options: { client_id: string; callback: (response: { credential: string }) => void }): void;
  renderButton(parent: HTMLElement, options: GoogleButtonOptions): void;
  disableAutoSelect(): void;
};

declare global {
  interface Window {
    google?: { accounts?: { id?: GoogleIdentityServices } };
  }
}

const SCRIPT_URL = "https://accounts.google.com/gsi/client";

let loading: Promise<GoogleIdentityServices> | null = null;
let initializedFor: string | null = null;
let onCredential: ((credential: string) => void) | null = null;

function loadGoogleIdentity(): Promise<GoogleIdentityServices> {
  const loaded = window.google?.accounts?.id;
  if (loaded) return Promise.resolve(loaded);
  loading ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCRIPT_URL;
    script.async = true;
    script.onload = () => {
      const id = window.google?.accounts?.id;
      if (id) resolve(id);
      else fail();
    };
    script.onerror = fail;
    document.head.appendChild(script);

    function fail() {
      // Let a later attempt try again.
      script.remove();
      loading = null;
      reject(new Error("Could not load Google sign-in. Check your connection, then reload the page."));
    }
  });
  return loading;
}

/**
 * Draw Google's sign-in button inside `parent`. When someone signs in, `onSignIn` gets the ID token
 * that Google issued for them, for the backend to verify.
 */
export async function renderGoogleButton(
  parent: HTMLElement,
  clientId: string,
  onSignIn: (credential: string) => void,
): Promise<void> {
  const id = await loadGoogleIdentity();
  onCredential = onSignIn;
  // Google asks for initialize() to be called once per page; the latest onSignIn is used through onCredential.
  if (initializedFor !== clientId) {
    id.initialize({ client_id: clientId, callback: (response) => onCredential?.(response.credential) });
    initializedFor = clientId;
  }
  // Google's button is between 200 and 400 pixels wide.
  const width = Math.min(400, Math.max(200, Math.floor(parent.clientWidth)));
  // Drawing again into the same place (React runs effects twice in development) replaces the button.
  parent.replaceChildren();
  // Google labels the button in the browser's language unless told otherwise; match the page instead.
  const locale = document.documentElement.lang || undefined;
  id.renderButton(parent, { type: "standard", theme: "outline", size: "large", text: "signin_with", width, locale });
}

/** After signing out, stop Google from signing the same account straight back in. */
export function forgetGoogleAccount() {
  window.google?.accounts?.id?.disableAutoSelect();
}
