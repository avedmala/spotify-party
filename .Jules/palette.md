## 2025-05-14 - [Accessibility and Usability Sweep]
**Learning:** The application relied heavily on implicit interactions (pressing Enter to submit) and lacked basic accessibility metadata (alt text, ARIA labels). Using `sr-only` labels in Bootstrap 4.4.1 allows for improving screen reader support without drastically altering the minimalist visual design. Adding visible submit buttons significantly improves the "affordance" of forms.
**Action:** Always check for `sr-only` labels and visible submit buttons when reviewing minimalist UIs. Ensure icon-only buttons have `aria-label`.
