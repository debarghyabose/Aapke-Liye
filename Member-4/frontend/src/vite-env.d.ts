/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Member 2 backend, e.g. http://localhost:8000. Unset = demo mode with sample data. */
  readonly VITE_API_URL?: string;
  /** Member 3 (mesh relay). Default http://localhost:8002 */
  readonly VITE_MESH_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
