export interface LearningResource {
  id: number
  resource_type: string
  title: string
  content: string
  rendered_html?: string
  metadata?: Record<string, unknown>
}

export interface Profile {
  major: string
  cognitive_style: string
  learning_goal: string
  weak_points: Array<{ name: string; confidence: number }>
  interests: string
}

export interface PathStep {
  step: number
  topic: string
  description: string
  estimated_minutes: number
  resource_types_needed: string[]
  status: 'pending' | 'in_progress' | 'completed'
}

export interface LearningPath {
  id: number
  path_data: PathStep[]
  current_step: number
  is_active: boolean
}
