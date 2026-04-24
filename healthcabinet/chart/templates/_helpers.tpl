{{/*
Expand the name of the chart.
*/}}
{{- define "healthcabinet.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "healthcabinet.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Chart label.
*/}}
{{- define "healthcabinet.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels.
*/}}
{{- define "healthcabinet.labels" -}}
helm.sh/chart: {{ include "healthcabinet.chart" . }}
{{ include "healthcabinet.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels.
*/}}
{{- define "healthcabinet.selectorLabels" -}}
app.kubernetes.io/name: {{ include "healthcabinet.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Component names.
*/}}
{{- define "healthcabinet.backend.fullname" -}}
{{- printf "%s-backend" (include "healthcabinet.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "healthcabinet.frontend.fullname" -}}
{{- printf "%s-frontend" (include "healthcabinet.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "healthcabinet.worker.fullname" -}}
{{- printf "%s-worker" (include "healthcabinet.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Name of the application Opaque secret (create-or-reference).
*/}}
{{- define "healthcabinet.appSecretName" -}}
{{- if .Values.appSecrets.existingSecret -}}
{{- .Values.appSecrets.existingSecret -}}
{{- else -}}
{{- printf "%s-app" (include "healthcabinet.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{/*
Sub-chart service hosts. Sub-charts use their release-scoped name by default.
*/}}
{{- define "healthcabinet.postgres.host" -}}
{{- printf "%s-postgres" .Release.Name -}}
{{- end -}}

{{- define "healthcabinet.redis.host" -}}
{{- printf "%s-redis" .Release.Name -}}
{{- end -}}

{{- define "healthcabinet.minio.host" -}}
{{- printf "%s-minio" .Release.Name -}}
{{- end -}}

{{/*
Image reference helpers. Registry may be empty, repo MUST be set.
*/}}
{{- define "healthcabinet.backend.image" -}}
{{- $reg := .Values.image.registry -}}
{{- $repo := .Values.image.backend.repository -}}
{{- $tag := default .Chart.AppVersion .Values.image.backend.tag -}}
{{- if $reg -}}
{{- printf "%s/%s:%s" $reg $repo $tag -}}
{{- else -}}
{{- printf "%s:%s" $repo $tag -}}
{{- end -}}
{{- end -}}

{{- define "healthcabinet.frontend.image" -}}
{{- $reg := .Values.image.registry -}}
{{- $repo := .Values.image.frontend.repository -}}
{{- $tag := default .Chart.AppVersion .Values.image.frontend.tag -}}
{{- if $reg -}}
{{- printf "%s/%s:%s" $reg $repo $tag -}}
{{- else -}}
{{- printf "%s:%s" $repo $tag -}}
{{- end -}}
{{- end -}}

{{/*
Shared env for backend + worker. Connection strings reference sub-chart secrets
so plaintext passwords never land in the Deployment spec. appSecrets are loaded
via envFrom in the Deployment template directly.
*/}}
{{- define "healthcabinet.backendEnv" -}}
{{- if .Values.postgres.enabled }}
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "healthcabinet.postgres.host" . }}
      key: postgres-password
- name: DATABASE_URL
  value: "postgresql+asyncpg://{{ .Values.postgres.auth.username }}:$(POSTGRES_PASSWORD)@{{ include "healthcabinet.postgres.host" . }}:{{ .Values.postgres.service.port }}/{{ .Values.postgres.auth.database }}"
{{- end }}
{{- if .Values.redis.enabled }}
- name: REDIS_URL
  value: "redis://{{ include "healthcabinet.redis.host" . }}:{{ .Values.redis.service.port }}"
{{- end }}
{{- if .Values.minio.enabled }}
- name: MINIO_ENDPOINT
  value: "{{ include "healthcabinet.minio.host" . }}:{{ .Values.minio.service.port }}"
- name: MINIO_ACCESS_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "healthcabinet.minio.host" . }}
      key: root-user
- name: MINIO_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "healthcabinet.minio.host" . }}
      key: root-password
- name: MINIO_BUCKET
  value: "healthcabinet"
{{- end }}
{{- range $k, $v := .Values.backend.env }}
- name: {{ $k }}
  value: {{ $v | quote }}
{{- end }}
{{- end -}}

{{/*
imagePullSecrets block — emitted only when imagePullSecret.create or a name is configured.
*/}}
{{- define "healthcabinet.imagePullSecrets" -}}
{{- if .Values.imagePullSecret.create }}
imagePullSecrets:
  - name: {{ .Values.imagePullSecret.name }}
{{- end }}
{{- end -}}
