import { apiFetch } from './backend';

export type FanRole = 'top' | 'center' | 'bottom';
export type MascotState = 'idle' | 'listening' | 'thinking' | 'speaking';

export interface FanUnitStatus {
  role: FanRole;
  enabled: boolean;
  ip: string;
  port: number;
  connected: boolean;
  current_index: number | null;
  current_media_id: string | null;
  last_error: string | null;
  worker_alive: boolean;
  requested_index?: number | null;
  last_sent_index?: number | null;
  last_send_result?: string | null;
  last_send_at?: number | null;
  semantic_id?: string | null;
  retry_count?: number;
  identify_index?: number;
}

export interface RotationMediaStatus {
  id: string;
  title: string;
  index: number;
  duration_seconds: number;
}

export interface IdentityMedia {
  id: string;
  title: string;
  index: number;
  enabled: boolean;
  default: boolean;
  keywords: string[];
}

export interface PromotionMedia {
  id: string;
  title: string;
  index: number;
  enabled: boolean;
  categories: string[];
  keywords: string[];
  duration_seconds: number;
  priority: number;
  rotation_enabled: boolean;
}

export interface RotationStatus {
  active?: boolean;
  paused?: boolean;
  current?: RotationMediaStatus | null;
  next?: RotationMediaStatus | null;
  context_id?: string | null;
  category?: string | null;
  last_error?: string | null;
  [key: string]: unknown;
}

export interface HologramStatus {
  status?: string;
  connected: boolean;
  ip: string;
  port: number;
  ai_paused?: boolean;
  units: FanUnitStatus[];
  rotation: RotationStatus;
  rotation_active?: boolean;
  current?: RotationMediaStatus | null;
  next?: RotationMediaStatus | null;
  context_id?: string | null;
  mode?: string;
  top_status?: FanUnitStatus;
}

export interface HologramApiError {
  status?: string;
  code?: string;
  message?: string;
  field?: string;
}

export interface UnitUpdate {
  enabled: boolean;
  ip: string;
  port: number;
  identify_index: number;
}

export interface IdentityPayload {
  id: string;
  title: string;
  index: number;
  enabled: boolean;
  default: boolean;
  keywords: string[];
}

export interface PromotionPayload {
  id: string;
  title: string;
  index: number;
  enabled: boolean;
  categories: string[];
  keywords: string[];
  topics: string[];
  duration_seconds: number;
  priority: number;
  rotation_enabled: boolean;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(path, init);
  const body = (await response.json()) as T & HologramApiError;
  if (!response.ok || body.status === 'error') {
    throw new Error(body.message || `La solicitud falló (${response.status}).`);
  }
  return body as T;
}

function jsonInit(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  };
}

export const hologramApi = {
  getStatus: () => request<HologramStatus>('/api/hologram/status'),
  getUnits: () => request<{ units: FanUnitStatus[] }>('/api/hologram/units'),
  updateUnit: (role: FanRole, payload: UnitUpdate) =>
    request<{ unit: FanUnitStatus }>(`/api/hologram/units/${role}`, jsonInit('PUT', payload)),
  unitAction: (role: FanRole, action: 'connect' | 'disconnect' | 'identify' | 'test', index?: number) =>
    request<Record<string, unknown>>(`/api/hologram/units/${role}/${action}`, index === undefined ? { method: 'POST' } : jsonInit('POST', { index })),
  getIdentities: () => request<{ identities: IdentityMedia[] }>('/api/hologram/identities'),
  createIdentity: (payload: IdentityPayload) =>
    request<{ identity: IdentityMedia }>('/api/hologram/identities', jsonInit('POST', payload)),
  updateIdentity: (id: string, payload: IdentityPayload) =>
    request<{ identity: IdentityMedia }>(`/api/hologram/identities/${encodeURIComponent(id)}`, jsonInit('PUT', payload)),
  deleteIdentity: (id: string) =>
    request<Record<string, unknown>>(`/api/hologram/identities/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  testIdentity: (id: string) =>
    request<Record<string, unknown>>(`/api/hologram/identities/${encodeURIComponent(id)}/test`, { method: 'POST' }),
  getPromotions: () => request<{ promotions: PromotionMedia[] }>('/api/hologram/promotions'),
  createPromotion: (payload: PromotionPayload) =>
    request<{ promotion: PromotionMedia }>('/api/hologram/promotions', jsonInit('POST', payload)),
  updatePromotion: (id: string, payload: PromotionPayload) =>
    request<{ promotion: PromotionMedia }>(`/api/hologram/promotions/${encodeURIComponent(id)}`, jsonInit('PUT', payload)),
  deletePromotion: (id: string) =>
    request<Record<string, unknown>>(`/api/hologram/promotions/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  testPromotion: (id: string) =>
    request<Record<string, unknown>>(`/api/hologram/promotions/${encodeURIComponent(id)}/test`, { method: 'POST' }),
  testCategory: (category: string) =>
    request<Record<string, unknown>>('/api/hologram/promotions/test-category', jsonInit('POST', { category })),
  rotationAction: (action: 'start' | 'pause' | 'resume' | 'stop') =>
    request<{ rotation: RotationStatus }>(`/api/hologram/rotation/${action}`, { method: 'POST' }),
};

export function splitTags(value: string): string[] {
  return [...new Set(value.split(',').map((item) => item.trim()).filter(Boolean))];
}
