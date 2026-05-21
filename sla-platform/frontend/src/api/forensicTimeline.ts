import client from "./client";

export interface TimelineSegment {
  queue_name: string;
  entered_at: string | null;
  exited_at: string | null;
  minutes_in_queue: number;
  response_timer_running: boolean;
  resolution_timer_running: boolean;
  paused: boolean;
  no_owner_minutes: number;
  response_loss_minutes: number;
  resolution_loss_minutes: number;
  owners_during: Array<{ owner: string; seconds: number; is_system: boolean }>;
  breach_inside_segment: boolean;
  queue_contribution_pct: number;
}

export interface TimelineResponse {
  ticket: {
    ticket_id: number;
    ticket_number: string;
    title: string | null;
    created_at: string | null;
    first_response_at: string | null;
    resolution_at: string | null;
    current_queue: string | null;
    current_state: string | null;
    current_owner: string | null;
    is_closed: boolean;
  };
  targets: {
    response_target_seconds: number;
    resolution_target_seconds: number;
  };
  segments: TimelineSegment[];
  summary: {
    total_minutes: number;
    total_segments: number;
    response_passed_in_queue: string | null;
    response_segments_pre_response: number;
    post_response_response_loss_violators: string[];
    top_loss_queue: string | null;
    top_loss_minutes: number;
    breach_queue: string | null;
    bounces: Array<{ queue: string; visits: number }>;
    first_response_rule_check: string;
  };
}

export const forensicTimelineApi = {
  forTicket: (
    ticketId: number,
    responseTargetSec = 1800,
    resolutionTargetSec = 28800,
  ) =>
    client.get<TimelineResponse>(
      `/analytics/forensics/timeline/${ticketId}`,
      { params: { response_target_seconds: responseTargetSec,
                  resolution_target_seconds: resolutionTargetSec } },
    ).then(r => r.data),
};
