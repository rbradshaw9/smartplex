// Generated types from Supabase CLI
// Run `pnpm supabase:types` from root to regenerate

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      users: {
        Row: {
          id: string
          email: string
          display_name: string | null
          avatar_url: string | null
          role: 'admin' | 'moderator' | 'user' | 'guest'
          plex_user_id: string | null
          plex_username: string | null
          created_at: string
          updated_at: string
          last_active_at: string | null
          preferences: Json | null
        }
        Insert: {
          id?: string
          email: string
          display_name?: string | null
          avatar_url?: string | null
          role?: 'admin' | 'moderator' | 'user' | 'guest'
          plex_user_id?: string | null
          plex_username?: string | null
          created_at?: string
          updated_at?: string
          last_active_at?: string | null
          preferences?: Json | null
        }
        Update: {
          id?: string
          email?: string
          display_name?: string | null
          avatar_url?: string | null
          role?: 'admin' | 'moderator' | 'user' | 'guest'
          plex_user_id?: string | null
          plex_username?: string | null
          created_at?: string
          updated_at?: string
          last_active_at?: string | null
          preferences?: Json | null
        }
      }
      servers: {
        Row: {
          id: string
          user_id: string
          name: string
          url: string
          machine_id: string | null
          platform: string | null
          version: string | null
          status: 'online' | 'offline' | 'error'
          last_seen_at: string | null
          created_at: string
          updated_at: string
          config: Json | null
        }
        Insert: {
          id?: string
          user_id: string
          name: string
          url: string
          machine_id?: string | null
          platform?: string | null
          version?: string | null
          status?: 'online' | 'offline' | 'error'
          last_seen_at?: string | null
          created_at?: string
          updated_at?: string
          config?: Json | null
        }
        Update: {
          id?: string
          user_id?: string
          name?: string
          url?: string
          machine_id?: string | null
          platform?: string | null
          version?: string | null
          status?: 'online' | 'offline' | 'error'
          last_seen_at?: string | null
          created_at?: string
          updated_at?: string
          config?: Json | null
        }
      }
      integrations: {
        Row: {
          id: string
          user_id: string
          server_id: string | null
          service: 'tautulli' | 'overseerr' | 'sonarr' | 'radarr' | 'trakt' | 'omdb'
          name: string
          url: string | null
          api_key: string | null
          config: Json | null
          status: 'active' | 'inactive' | 'error'
          last_sync_at: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          user_id: string
          server_id?: string | null
          service: 'tautulli' | 'overseerr' | 'sonarr' | 'radarr' | 'trakt' | 'omdb'
          name: string
          url?: string | null
          api_key?: string | null
          config?: Json | null
          status?: 'active' | 'inactive' | 'error'
          last_sync_at?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          server_id?: string | null
          service?: 'tautulli' | 'overseerr' | 'sonarr' | 'radarr' | 'trakt' | 'omdb'
          name?: string
          url?: string | null
          api_key?: string | null
          config?: Json | null
          status?: 'active' | 'inactive' | 'error'
          last_sync_at?: string | null
          created_at?: string
          updated_at?: string
        }
      }
      media_items: {
        Row: {
          id: string
          server_id: string
          plex_id: string
          type: 'movie' | 'show' | 'season' | 'episode' | 'track' | 'album' | 'artist'
          title: string
          year: number | null
          imdb_id: string | null
          tmdb_id: number | null
          tvdb_id: number | null
          library_section: string | null
          file_path: string | null
          file_size_bytes: number | null
          duration_ms: number | null
          added_at: string
          updated_at: string
          metadata: Json | null
        }
        Insert: {
          id?: string
          server_id: string
          plex_id: string
          type: 'movie' | 'show' | 'season' | 'episode' | 'track' | 'album' | 'artist'
          title: string
          year?: number | null
          imdb_id?: string | null
          tmdb_id?: number | null
          tvdb_id?: number | null
          library_section?: string | null
          file_path?: string | null
          file_size_bytes?: number | null
          duration_ms?: number | null
          added_at?: string
          updated_at?: string
          metadata?: Json | null
        }
        Update: {
          id?: string
          server_id?: string
          plex_id?: string
          type?: 'movie' | 'show' | 'season' | 'episode' | 'track' | 'album' | 'artist'
          title?: string
          year?: number | null
          imdb_id?: string | null
          tmdb_id?: number | null
          tvdb_id?: number | null
          library_section?: string | null
          file_path?: string | null
          file_size_bytes?: number | null
          duration_ms?: number | null
          added_at?: string
          updated_at?: string
          metadata?: Json | null
        }
      }
      user_stats: {
        Row: {
          id: string
          user_id: string
          media_item_id: string
          play_count: number
          total_duration_ms: number
          last_played_at: string | null
          completion_percentage: number | null
          rating: number | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          user_id: string
          media_item_id: string
          play_count?: number
          total_duration_ms?: number
          last_played_at?: string | null
          completion_percentage?: number | null
          rating?: number | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          media_item_id?: string
          play_count?: number
          total_duration_ms?: number
          last_played_at?: string | null
          completion_percentage?: number | null
          rating?: number | null
          created_at?: string
          updated_at?: string
        }
      }
      cleanup_log: {
        Row: {
          id: string
          server_id: string
          media_item_id: string | null
          action: 'deleted' | 'quarantined' | 'moved' | 'analyzed'
          file_path: string
          file_size_bytes: number | null
          reason: string
          performed_by: string | null
          performed_at: string
          metadata: Json | null
        }
        Insert: {
          id?: string
          server_id: string
          media_item_id?: string | null
          action: 'deleted' | 'quarantined' | 'moved' | 'analyzed'
          file_path: string
          file_size_bytes?: number | null
          reason: string
          performed_by?: string | null
          performed_at?: string
          metadata?: Json | null
        }
        Update: {
          id?: string
          server_id?: string
          media_item_id?: string | null
          action?: 'deleted' | 'quarantined' | 'moved' | 'analyzed'
          file_path?: string
          file_size_bytes?: number | null
          reason?: string
          performed_by?: string | null
          performed_at?: string
          metadata?: Json | null
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      user_role: 'admin' | 'moderator' | 'user' | 'guest'
      server_status: 'online' | 'offline' | 'error'
      integration_service: 'tautulli' | 'overseerr' | 'sonarr' | 'radarr' | 'trakt' | 'omdb'
      integration_status: 'active' | 'inactive' | 'error'
      media_type: 'movie' | 'show' | 'season' | 'episode' | 'track' | 'album' | 'artist'
      cleanup_action: 'deleted' | 'quarantined' | 'moved' | 'analyzed'
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}