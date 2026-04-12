import { createLovableConfig } from "lovable-agent-playwright-config/config";

export default createLovableConfig({
  timeout: 60000,
  use: {
    baseURL: 'https://id-preview--8044fe8a-a0dd-48df-8cc9-f8809f9d8972.lovable.app',
  },
});
