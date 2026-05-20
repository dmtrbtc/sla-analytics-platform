{{/* Generate basic labels */}}
{{- define "sla-platform.labels" -}}
app.kubernetes.io/name: sla-platform
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/* Generate hostname */}}
{{- define "sla-platform.hostname" -}}
{{- if .Values.global.domain -}}
{{ .Values.global.domain }}
{{- else -}}
sla.example.com
{{- end -}}
{{- end -}}
