{{- define "microservice.name" -}}
{{ .Values.name }}
{{- end }}

{{- define "microservice.fullname" -}}
{{ .Values.name }}
{{- end }}

{{- define "microservice.namespace" -}}
{{ .Values.namespace }}
{{- end }}
