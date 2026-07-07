import type { DetailedHTMLProps, HTMLAttributes } from 'react'

// Register the <model-viewer> web component (from @google/model-viewer) as a
// JSX intrinsic element. React 19's automatic runtime resolves intrinsic
// elements against React.JSX, so we augment the 'react' module here rather
// than a global `namespace JSX` (which the runtime ignores).
declare module 'react' {
  namespace JSX {
    interface IntrinsicElements {
      'model-viewer': DetailedHTMLProps<HTMLAttributes<HTMLElement>, HTMLElement> & {
        src?: string
        alt?: string
        'camera-controls'?: boolean | string
        'auto-rotate'?: boolean | string
        'shadow-intensity'?: string
        ar?: boolean | string
      }
    }
  }
}
