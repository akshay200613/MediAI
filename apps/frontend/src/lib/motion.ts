/**
 * Shared Motion Design Tokens
 * Centralized framer-motion presets for consistent animation across MedAI.
 */

import type { Transition, Variants } from 'framer-motion'

/* ── Spring Presets ─────────────────────────────────── */

export const springSnappy: Transition = {
  type: 'spring',
  stiffness: 400,
  damping: 30,
}

export const springSmooth: Transition = {
  type: 'spring',
  stiffness: 200,
  damping: 25,
}

export const springBouncy: Transition = {
  type: 'spring',
  stiffness: 300,
  damping: 15,
}

/* ── Easing Presets ─────────────────────────────────── */

export const easeOutExpo: Transition = {
  duration: 0.5,
  ease: [0.16, 1, 0.3, 1],
}

/* ── Stagger Containers ─────────────────────────────── */

export const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.06,
    },
  },
}

export const staggerContainerSlow: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.12,
    },
  },
}

export const staggerContainerFast: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.04,
    },
  },
}

/* ── Item Variants ──────────────────────────────────── */

/** Fade + slide up — ideal for cards, list items */
export const fadeSlideUp: Variants = {
  hidden: { opacity: 0, y: 20 },
  show: {
    opacity: 1,
    y: 0,
    transition: easeOutExpo,
  },
}

/** Fade + scale up — ideal for stat cards */
export const fadeScaleUp: Variants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: easeOutExpo,
  },
}

/** Slide from left — ideal for timeline items */
export const slideFromLeft: Variants = {
  hidden: { opacity: 0, x: -16 },
  show: {
    opacity: 1,
    x: 0,
    transition: easeOutExpo,
  },
}

/** Slide from right — ideal for user chat bubbles */
export const slideFromRight: Variants = {
  hidden: { opacity: 0, x: 20 },
  show: {
    opacity: 1,
    x: 0,
    transition: easeOutExpo,
  },
}

/* ── Page Transition ────────────────────────────────── */

export const pageTransition: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] },
  },
  exit: {
    opacity: 0,
    y: -4,
    transition: { duration: 0.2 },
  },
}

/* ── Interactive Presets ─────────────────────────────── */

export const tapScale = { scale: 0.97 }
export const tapScaleSmall = { scale: 0.95 }
export const tapScaleLarge = { scale: 0.9 }

export const hoverLift = {
  y: -4,
  boxShadow: '0 12px 40px rgba(0, 0, 0, 0.3)',
  transition: springSnappy,
}

export const hoverGlow = {
  scale: 1.02,
  boxShadow: '0 0 30px rgba(20, 184, 166, 0.4)',
}

export const hoverChip = {
  scale: 1.04,
  y: -2,
}

/* ── Dropdown / Popover ─────────────────────────────── */

export const dropdownVariants: Variants = {
  hidden: { opacity: 0, scale: 0.9, y: -8 },
  show: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: springSnappy,
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: -4,
    transition: { duration: 0.15 },
  },
}
