import type { Transition, Variants } from 'motion/react'

export const ease = [0.22, 1, 0.36, 1] as const
export const spring: Transition = { type: 'spring', stiffness: 380, damping: 32 }

export const pageVariants: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.28, ease } },
  exit: { opacity: 0, transition: { duration: 0.12 } },
}

export const stagger: Variants = { animate: { transition: { staggerChildren: 0.05 } } }
export const rise: Variants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.32, ease } },
}
export const fade: Variants = { initial: { opacity: 0 }, animate: { opacity: 1, transition: { duration: 0.2 } }, exit: { opacity: 0, transition: { duration: 0.12 } } }
export const modal: Variants = {
  initial: { opacity: 0, scale: 0.97, y: 8 },
  animate: { opacity: 1, scale: 1, y: 0, transition: { duration: 0.2, ease } },
  exit: { opacity: 0, scale: 0.98, transition: { duration: 0.12 } },
}
