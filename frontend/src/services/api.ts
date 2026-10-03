import type { Dashboard } from '../types/dashboard'
import type { ActivityEvent, AssistantReply, GlucoseReading, Meal, Medicine, SleepEvent, Memory, WeeklyReport, Notification } from '../types/health'
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
export const getGlucose = (hours = 24) => request<GlucoseReading[]>(`/api/glucose/history?hours=${hours}`)
export const getMedicines = () => request<Medicine[]>('/api/medicines')
export const confirmMedicine = (id: number, time: string) => request<Medicine>(`/api/medicines/${id}/confirm`, { method: 'POST', body: JSON.stringify({ time_of_day: time }) })
export const getMeals = () => request<Meal[]>('/api/meals')
export const logMeal = (description: string, meal_type: string) => request<Meal>('/api/meals', { method: 'POST', body: JSON.stringify({ description, meal_type }) })
export const getActivities = () => request<ActivityEvent[]>('/api/activities')
export const getSleep = () => request<SleepEvent[]>('/api/sleep')
export const askSugarPath = (message: string) => request<AssistantReply>('/api/assistant/chat', { method: 'POST', body: JSON.stringify({ message }) })
export const getMemories = () => request<Memory[]>('/api/memories')
export const deleteMemory = (id: number) => request<void>(`/api/memories/${id}`, { method: 'DELETE' })
export const getCurrentWeeklyReport = () => request<WeeklyReport>('/api/reports/weekly/current')
export const generateWeeklyReport = () => request<WeeklyReport>('/api/reports/weekly/generate', { method: 'POST', body: JSON.stringify({}) })
export const getNotifications = () => request<Notification[]>('/api/notifications')
export const evaluateEvents = () => request<{ events_created: number; notifications_created: number }>('/api/events/evaluate', { method: 'POST' })
export const setNotificationRead = (id: number) => request<Notification>(`/api/notifications/${id}/read`, { method: 'PATCH' })
export const dismissNotification = (id: number) => request<Notification>(`/api/notifications/${id}/dismiss`, { method: 'PATCH' })
