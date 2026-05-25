from rest_framework import permissions
from django.http import HttpResponse
from rest_framework import renderers
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.schemas import get_schema_view


class StableAutoSchema(AutoSchema):
    def get_operation_id_base(self, path, method, action):
        model = getattr(getattr(self.view, "queryset", None), "model", None)

        if self.operation_id_base is not None:
            name = self.operation_id_base
        elif model is not None:
            name = model.__name__
        elif self.get_serializer(path, method) is not None:
            name = self.get_serializer(path, method).__class__.__name__
            if name.endswith("Serializer"):
                name = name[:-10]
        else:
            name = self.view.__class__.__name__
            if name.endswith("APIView"):
                name = name[:-7]
            elif name.endswith("View"):
                name = name[:-4]
            if name.endswith(action.title()):
                name = name[:-len(action)]

        if action == "list" and not name.endswith("s"):
            name = f"{name}s"
        return name


schema_view = get_schema_view(
    title="AML Check Enterprise API",
    version="1.0.0",
    renderer_classes=[renderers.JSONOpenAPIRenderer],
    public=True,
    authentication_classes=[],
    permission_classes=[permissions.AllowAny],
)

SWAGGER_TEMPLATE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>AML Check Enterprise - Swagger</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
    <style>
      body { margin: 0; background: #04111d; }
      #swagger-ui { max-width: 1400px; margin: 0 auto; }
    </style>
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      window.ui = SwaggerUIBundle({ url: '/api/schema/', dom_id: '#swagger-ui' });
    </script>
  </body>
</html>
"""

REDOC_TEMPLATE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>AML Check Enterprise - ReDoc</title>
    <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
  </head>
  <body>
    <redoc spec-url="/api/schema/"></redoc>
  </body>
</html>
"""


def swagger_ui(request):
    return HttpResponse(SWAGGER_TEMPLATE)


def redoc_ui(request):
    return HttpResponse(REDOC_TEMPLATE)
