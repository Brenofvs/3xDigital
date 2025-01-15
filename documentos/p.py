import os

def create_project_structure(base_dir):
    # Estrutura de diretórios
    dirs = [
        "app", "app/models", "app/views", "app/services", "app/utils", "app/tests",
        "frontend", "frontend/public", "frontend/src", "frontend/src/components",
        "frontend/src/pages", "frontend/src/styles", "frontend/src/utils", "frontend/tests",
        "mobile", "mobile/android", "mobile/ios", "mobile/shared",
        "infra", "infra/docker", "infra/kubernetes", "infra/ci-cd", "infra/scripts", "infra/monitoring",
        "docs", "docs/api", "docs/architecture", "docs/user-guides",
        "static", "static/images", "static/pdfs", "static/uploads"
    ]

    # Criar os diretórios
    for dir_path in dirs:
        path = os.path.join(base_dir, dir_path)
        os.makedirs(path, exist_ok=True)

    print(f"Estrutura de diretórios criada em: {base_dir}")

if __name__ == "__main__":
    # Diretório base onde a estrutura será criada
    base_dir = "D:\#3xDigital"  # Altere para o caminho desejado
    create_project_structure(base_dir)
