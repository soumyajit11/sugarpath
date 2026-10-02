import type { Dashboard } from '../types/dashboard'
import type { ActivityEvent, AssistantReply, GlucoseReading, Meal, Medicine, SleepEvent } from '../types/health'
// Keep the browser default aligned with the local backend bind address.
// This avoids localhost resolving to IPv6 (::1) on some Windows setups.
const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'
export async function getDashboard(): Promise<Dashboard> {
  const response = await fetch(`${API_URL}/api/dashboard`)
  if (!response.ok) throw new Error('We could not load your dashboard.')
  return response.json()
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options })
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail ?? 'Something went wrong.') }
  return response.json()
}
export const getGlucose = () => request<GlucoseReading[]>('/api/glucose/history?hours=24')
export const getMedicines = () => request<Medicine[]>('/api/medicines')
export const confirmMedicine = (id: number, time: string) => request<Medicine>(`/api/medicines/${id}/confirm`, { method: 'POST', body: JSON.stringify({ time_of_day: time }) })
export const getMeals = () => request<Meal[]>('/api/meals')
export const logMeal = (description: string, meal_type: string) => request<Meal>('/api/meals', { method: 'POST', body: JSON.stringify({ description, meal_type }) })
export const getActivities = () => request<ActivityEvent[]>('/api/activities')
export const getSleep = () => request<SleepEvent[]>('/api/sleep')
export const askSugarPath = (message: string) => request<AssistantReply>('/api/assistant/chat', { method: 'POST', body: JSON.stringify({ message }) })
