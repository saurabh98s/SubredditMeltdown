import os
import unittest
import sys

class TestEnvironment(unittest.TestCase):
    """Test the environment setup for the project."""
    
    def test_project_structure(self):
        """Test that the key project directories exist."""
        # Get the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Key directories that should exist
        directories = [
            'data',
            'data_ingestion',
            'pyspark_jobs',
            'backend',
            'frontend',
            'docs',
            'tests',
            'infra'
        ]
        
        for directory in directories:
            dir_path = os.path.join(project_root, directory)
            self.assertTrue(os.path.isdir(dir_path), f"Directory not found: {directory}")
    
    def test_backend_api_exists(self):
        """Test that the backend API file exists."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        api_path = os.path.join(project_root, 'backend', 'api', 'main.py')
        self.assertTrue(os.path.isfile(api_path), "Backend API main.py not found")
    
    def test_frontend_files_exist(self):
        """Test that key frontend files exist."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        frontend_files = [
            os.path.join('frontend', 'package.json'),
            os.path.join('frontend', 'src', 'pages', 'index.tsx')
        ]
        
        for file_path in frontend_files:
            full_path = os.path.join(project_root, file_path)
            self.assertTrue(os.path.isfile(full_path), f"Frontend file not found: {file_path}")
    
    def test_docker_compose_exists(self):
        """Test that the docker-compose.yml file exists."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        docker_compose_path = os.path.join(project_root, 'docker-compose.yml')
        self.assertTrue(os.path.isfile(docker_compose_path), "docker-compose.yml not found")

if __name__ == '__main__':
    unittest.main() 