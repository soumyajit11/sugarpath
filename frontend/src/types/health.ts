export type GlucoseReading = { timestamp: string; value_mg_dl: number; trend: string | null; source: string; synthetic: boolean }
export type Medicine = { id: number; name: string; dose: string; time_of_day: string; instructions: string; status: string; event_time: string | null }
export type Meal = { id: number; timestamp: string; meal_type: string; description: string; estimated_carbs_g: number; items: string[] }
export type ActivityEvent = { timestamp: string; activity_type: string; duration_minutes: number; steps: number | null }
export type SleepEvent = { start_time: string; end_time: string; quality: string | null; duration_minutes: number }
export type AssistantReply = { message: string; sources_used: string[]; status: string }
