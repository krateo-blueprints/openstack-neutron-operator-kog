{{/*
Expand the name of the chart.
*/}}
{{- define "openstack-neutron-operator-kog.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "openstack-neutron-operator-kog.fullname" -}}
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
Chart label.
*/}}
{{- define "openstack-neutron-operator-kog.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "openstack-neutron-operator-kog.labels" -}}
helm.sh/chart: {{ include "openstack-neutron-operator-kog.chart" . }}
{{ include "openstack-neutron-operator-kog.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "openstack-neutron-operator-kog.selectorLabels" -}}
app.kubernetes.io/name: {{ include "openstack-neutron-operator-kog.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Auth-bridge resource name.
*/}}
{{- define "openstack-neutron-operator-kog.authBridgeName" -}}
{{- printf "%s-auth-bridge" (include "openstack-neutron-operator-kog.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
In-cluster URL the generated controller should hit instead of the real
upstream Keystone endpoint. The auth-bridge listens here and rewrites
headers before forwarding to .Values.authBridge.upstreamUrl.
*/}}
{{- define "openstack-neutron-operator-kog.authBridgeUrl" -}}
http://{{ include "openstack-neutron-operator-kog.authBridgeName" . }}.{{ .Release.Namespace }}.svc.cluster.local:{{ .Values.authBridge.service.port }}
{{- end -}}
