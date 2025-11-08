export * from './utils'
export * from './api'

// Common constants
export const APP_NAME = 'SmartPlex'
export const APP_VERSION = '0.1.0'
export const API_VERSION = 'v1'

// Default pagination
export const DEFAULT_PAGE_SIZE = 20
export const MAX_PAGE_SIZE = 100

// File size limits (in bytes)
export const MAX_UPLOAD_SIZE = 10 * 1024 * 1024 // 10MB
export const MAX_AVATAR_SIZE = 2 * 1024 * 1024 // 2MB

// Date formats
export const DATE_FORMAT = 'yyyy-MM-dd'
export const DATETIME_FORMAT = 'yyyy-MM-dd HH:mm:ss'
export const TIME_FORMAT = 'HH:mm:ss'

// Media types
export const MEDIA_TYPES = ['movie', 'show', 'season', 'episode', 'track', 'album', 'artist'] as const
export type MediaType = typeof MEDIA_TYPES[number]

// User roles
export const USER_ROLES = ['admin', 'moderator', 'user', 'guest'] as const
export type UserRole = typeof USER_ROLES[number]

// Integration services
export const INTEGRATION_SERVICES = ['tautulli', 'overseerr', 'sonarr', 'radarr', 'trakt', 'omdb'] as const
export type IntegrationService = typeof INTEGRATION_SERVICES[number]