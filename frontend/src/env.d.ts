/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/ban-types
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare module 'splitpanes' {
    import { DefineComponent } from 'vue';
    export const Splitpanes: DefineComponent<any, any, any>;
    export const Pane: DefineComponent<any, any, any>;
}
