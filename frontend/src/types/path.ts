export type PathStepStatus = 'pending' | 'in_progress' | 'completed'
export type PathResourceType = 'document' | 'quiz' | 'mindmap' | 'video_script' | 'code_case'

export interface PathStep {
  step: number
  topic: string
  description: string
  estimated_minutes: number
  resource_types_needed: PathResourceType[]
  status: PathStepStatus
}

export interface LearningPath {
  id: number
  path_data: PathStep[]
  current_step: number
  is_active: boolean
}

export interface GeneratePathInput { message: string; course: string }
