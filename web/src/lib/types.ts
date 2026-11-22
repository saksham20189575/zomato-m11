export type BudgetBand = "low" | "medium" | "high";

export type ServiceStatus = "success" | "empty" | "error";

export type RecommendationSource = "llm" | "fallback";

export interface Recommendation {
  restaurant_id: string;
  name: string;
  rank: number;
  cuisine: string;
  rating: number;
  estimated_cost: number | null;
  explanation: string;
}

export interface RecommendationResult {
  summary: string | null;
  recommendations: Recommendation[];
  source: RecommendationSource;
  note: string | null;
}

export interface UserPreferences {
  location: string;
  budget: BudgetBand;
  cuisine: string | null;
  min_rating: number;
  additional_preferences: string | null;
  top_k: number | null;
}

export interface ServiceResult {
  status: ServiceStatus;
  preferences: UserPreferences | null;
  shortlist_size: number;
  result: RecommendationResult | null;
  empty_reason_code: string | null;
  message: string | null;
  model_name: string | null;
}

export interface MetaResponse {
  locations: string[];
  cuisines: string[];
  default_top_k: number;
  max_candidates: number;
  has_llm_key: boolean;
}

export interface RecommendRequest {
  location: string;
  budget: BudgetBand;
  cuisine?: string | null;
  min_rating: number;
  additional_preferences?: string | null;
  top_k?: number | null;
  mock?: boolean;
}

export type UiView = "idle" | "loading" | "live" | "empty" | "error";
