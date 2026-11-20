/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Member 2 backend, e.g. http://localhost:8000. Unset = demo mode with sample data. */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
