export interface AuthToken {
  access_token: string
  token_type: string
}

export type LearningStyle = 'visual' | 'auditory' | 'hands_on' | 'theoretical'

export interface User {
  id: number
  username: string
  email: string
  learning_style: LearningStyle
}

export interface Credentials {
  username: string
  password: string
}

export interface RegistrationInput extends Credentials {
  email: string
  learning_style: LearningStyle
}
