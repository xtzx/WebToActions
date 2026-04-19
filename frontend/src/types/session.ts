export interface BrowserSessionSummary {
  id: string;
  profileId: string;
  status: string;
  loginSiteSummaries: string[];
  createdAt: string;
  lastActivityAt: string;
}

export interface BrowserSessionListResponse {
  items: BrowserSessionSummary[];
}
