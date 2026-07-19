{{- define "mohamed-mar-app.fullname" -}}
{{ .Values.releaseName }}
{{- end -}}

{{- define "mohamed-mar-app.labels" -}}
app: {{ .Values.releaseName }}
student: {{ .Values.student | quote }}
{{- end -}}
