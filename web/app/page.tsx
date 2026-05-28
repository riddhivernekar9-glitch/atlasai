/**
 * Root page — middleware handles the smart redirect (/ → /dashboard or /login).
 * This component is a fallback that never renders in practice.
 */
import { redirect } from 'next/navigation'

export default function Home() {
  redirect('/login')
}
