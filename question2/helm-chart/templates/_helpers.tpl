{{/*
Expand the name of the chart.
*/}}
{{- define "microservices-app.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "microservices-app.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "microservices-app.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "microservices-app.labels" -}}
helm.sh/chart: {{ include "microservices-app.chart" . }}
{{ include "microservices-app.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "microservices-app.selectorLabels" -}}
app.kubernetes.io/name: {{ include "microservices-app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "microservices-app.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "microservices-app.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
API Service labels
*/}}
{{- define "microservices-app.apiService.labels" -}}
{{ include "microservices-app.labels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
API Service selector labels
*/}}
{{- define "microservices-app.apiService.selectorLabels" -}}
{{ include "microservices-app.selectorLabels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
Worker Service labels
*/}}
{{- define "microservices-app.workerService.labels" -}}
{{ include "microservices-app.labels" . }}
app.kubernetes.io/component: worker
{{- end }}

{{/*
Worker Service selector labels
*/}}
{{- define "microservices-app.workerService.selectorLabels" -}}
{{ include "microservices-app.selectorLabels" . }}
app.kubernetes.io/component: worker
{{- end }}

{{/*
Frontend Service labels
*/}}
{{- define "microservices-app.frontendService.labels" -}}
{{ include "microservices-app.labels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Frontend Service selector labels
*/}}
{{- define "microservices-app.frontendService.selectorLabels" -}}
{{ include "microservices-app.selectorLabels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Database labels
*/}}
{{- define "microservices-app.database.labels" -}}
{{ include "microservices-app.labels" . }}
app.kubernetes.io/component: database
{{- end }}

{{/*
Database selector labels
*/}}
{{- define "microservices-app.database.selectorLabels" -}}
{{ include "microservices-app.selectorLabels" . }}
app.kubernetes.io/component: database
{{- end }}

{{/*
Create image name
*/}}
{{- define "microservices-app.image" -}}
{{- $registry := .Values.global.imageRegistry | default .Values.image.registry -}}
{{- $repository := .Values.image.repository -}}
{{- $tag := .Values.image.tag | default .Chart.AppVersion -}}
{{- if $registry }}
{{- printf "%s/%s/%s:%s" $registry $repository .component $tag }}
{{- else }}
{{- printf "%s/%s:%s" $repository .component $tag }}
{{- end }}
{{- end }}

{{/*
Create API service image
*/}}
{{- define "microservices-app.apiService.image" -}}
{{- $registry := .Values.global.imageRegistry | default .Values.image.registry -}}
{{- $repository := .Values.image.repository -}}
{{- $tag := .Values.apiService.image.tag | default .Values.image.tag | default .Chart.AppVersion -}}
{{- $component := .Values.apiService.image.repository | default .Values.apiService.name -}}
{{- if $registry }}
{{- printf "%s/%s/%s:%s" $registry $repository $component $tag }}
{{- else }}
{{- printf "%s/%s:%s" $repository $component $tag }}
{{- end }}
{{- end }}

{{/*
Create Worker service image
*/}}
{{- define "microservices-app.workerService.image" -}}
{{- $registry := .Values.global.imageRegistry | default .Values.image.registry -}}
{{- $repository := .Values.image.repository -}}
{{- $tag := .Values.workerService.image.tag | default .Values.image.tag | default .Chart.AppVersion -}}
{{- $component := .Values.workerService.image.repository | default .Values.workerService.name -}}
{{- if $registry }}
{{- printf "%s/%s/%s:%s" $registry $repository $component $tag }}
{{- else }}
{{- printf "%s/%s:%s" $repository $component $tag }}
{{- end }}
{{- end }}

{{/*
Create Frontend service image
*/}}
{{- define "microservices-app.frontendService.image" -}}
{{- $registry := .Values.global.imageRegistry | default .Values.image.registry -}}
{{- $repository := .Values.image.repository -}}
{{- $tag := .Values.frontendService.image.tag | default .Values.image.tag | default .Chart.AppVersion -}}
{{- $component := .Values.frontendService.image.repository | default .Values.frontendService.name -}}
{{- if $registry }}
{{- printf "%s/%s/%s:%s" $registry $repository $component $tag }}
{{- else }}
{{- printf "%s/%s:%s" $repository $component $tag }}
{{- end }}
{{- end }}

{{/*
Create Database image
*/}}
{{- define "microservices-app.database.image" -}}
{{- $registry := .Values.global.imageRegistry | default .Values.image.registry -}}
{{- $repository := .Values.database.image.repository -}}
{{- $tag := .Values.database.image.tag -}}
{{- if $registry }}
{{- printf "%s/%s:%s" $registry $repository $tag }}
{{- else }}
{{- printf "%s:%s" $repository $tag }}
{{- end }}
{{- end }}
