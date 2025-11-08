import { createClient } from '@supabase/supabase-js'
import type { Database } from '@smartplex/db'

/**
 * Environment variable configuration
 */
interface EnvConfig {
  supabaseUrl: string
  supabaseAnonKey: string
  supabaseServiceKey?: string
}

/**
 * Load environment variables with validation
 */
export function loadEnvConfig(): EnvConfig {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY
  const supabaseServiceKey = process.env.SUPABASE_SERVICE_KEY

  if (!supabaseUrl) {
    throw new Error('Missing SUPABASE_URL environment variable')
  }

  if (!supabaseAnonKey) {
    throw new Error('Missing SUPABASE_ANON_KEY environment variable')
  }

  return {
    supabaseUrl,
    supabaseAnonKey,
    supabaseServiceKey,
  }
}

/**
 * Create Supabase client for browser/client-side usage
 */
export function createSupabaseClient() {
  const config = loadEnvConfig()
  return createClient<Database>(config.supabaseUrl, config.supabaseAnonKey)
}

/**
 * Create Supabase admin client with service key (server-side only)
 */
export function createSupabaseAdmin() {
  const config = loadEnvConfig()
  
  if (!config.supabaseServiceKey) {
    throw new Error('Missing SUPABASE_SERVICE_KEY for admin client')
  }

  return createClient<Database>(config.supabaseUrl, config.supabaseServiceKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false
    }
  })
}

/**
 * API response wrapper with consistent error handling
 */
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: {
    message: string
    code?: string
    details?: any
  }
  meta?: {
    total?: number
    page?: number
    limit?: number
  }
}

/**
 * Create successful API response
 */
export function createSuccessResponse<T>(data: T, meta?: ApiResponse<T>['meta']): ApiResponse<T> {
  return {
    success: true,
    data,
    ...(meta && { meta }),
  }
}

/**
 * Create error API response
 */
export function createErrorResponse(
  message: string,
  code?: string,
  details?: any
): ApiResponse {
  return {
    success: false,
    error: {
      message,
      code,
      details,
    },
  }
}

/**
 * HTTP client with error handling
 */
export class ApiClient {
  private baseUrl: string
  private defaultHeaders: Record<string, string>

  constructor(baseUrl: string, defaultHeaders: Record<string, string> = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, '') // Remove trailing slash
    this.defaultHeaders = defaultHeaders
  }

  async request<T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const url = `${this.baseUrl}${endpoint}`
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...this.defaultHeaders,
          ...options.headers,
        },
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        return createErrorResponse(
          errorData.message || `HTTP ${response.status}`,
          response.status.toString(),
          errorData
        )
      }

      const data = await response.json()
      return createSuccessResponse(data)
    } catch (error) {
      return createErrorResponse(
        error instanceof Error ? error.message : 'Unknown error occurred'
      )
    }
  }

  async get<T = any>(endpoint: string, params?: Record<string, string>): Promise<ApiResponse<T>> {
    const url = params ? `${endpoint}?${new URLSearchParams(params)}` : endpoint
    return this.request<T>(url, { method: 'GET' })
  }

  async post<T = any>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async put<T = any>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async delete<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' })
  }
}

/**
 * Create API client for SmartPlex backend
 */
export function createApiClient(authToken?: string) {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const headers: Record<string, string> = {}
  
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
  }

  return new ApiClient(baseUrl, headers)
}