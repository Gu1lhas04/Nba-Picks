# 🏀 NBA Best-Props

<div align="center">

![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![Ngrok](https://img.shields.io/badge/Ngrok-1F1E37?style=for-the-badge&logo=ngrok&logoColor=white)

</div>

## 📋 Sobre o Projeto

O NBA Best-Props é uma plataforma sofisticada que combina análise de dados e estatísticas avançadas para fornecer insights valiosos sobre jogos da NBA. O sistema permite que utilizadores façam apostas informadas baseadas em análises estatísticas profundas.

### 🎯 Objetivos

- Fornecer uma plataforma intuitiva para apostas em jogadores da NBA
- Implementar análises estatísticas avançadas de jogadores
- Apresentar as melhores apostas possíveis consoante os últimos 10 jogos
- Criar visualizações interativas e informativas (Exemplos: Gráfico de Lucro do Utilizador)
- Oferecer uma experiência de utilizador moderna

## ✨ Funcionalidades Principais

### 🎲 Sistema de Apostas Simples
- Apostas Realizadas quando visualizado a estatística de um jogador (verificação se tem jogo breve)
- Sistema de odds dinâmicas
- Histórico de apostas
- Estatísticas de performance (Gráfico)

### 📊 Análise Estatística
- Visualizar possiveis plantéis inicias de cada jogo (Informação importante na realização das apostas)
- Análise de performance de jogadores
- Comparativos históricos
- Tendências de época

### 🔮 Previsões
- Análise de tendências
- Insights personalizados

### 📱 Interface
- Design personalizado
- Visualizações interativas com Plotly
- Dashboard personalizado

## 🛠️ Stack Tecnológica

### Backend
- **Framework**: Django 5.1.3
- **Linguagem**: Python 3.x
- **Base de Dados**: PostgreSQL
- **API**: NBA API
- **Processamento de Dados**: Pandas, NumPy
- **Visualização**: Plotly, Matplotlib
- **Web Scraping**: BeautifulSoup4

### Frontend
- **Design**: 
  - Prototipagem e UI/UX no [Figma](https://www.figma.com/design/dfUqlcETMUqNOeiIZfczik/Projeto-Final?node-id=0-1&t=sWD2PcRY4ZpDET7P-1)
  
  ![Protótipo Figma](docs/images/prototipos.png)

- **HTML/CSS**: Desenvolvimento personalizado
- **JavaScript**: jQuery para interatividade
- **Gráficos**: Plotly.js para visualizações dinâmicas
- **Templates**: Django Templates com estrutura modular

### DevOps
- **Versionamento**: Git
- **Servidor Local**: Django Development Server
- **Túnel de Servidor**: Ngrok (para acesso remoto e Deploy)
- **Gestão de Dependências**: pip
- **Ambiente Virtual**: venv

## 🚀 Começando (para Utilização Local)

### Pré-requisitos

- Python 3.8 ou superior
- PostgreSQL 12 ou superior
- pip (gestor de pacotes Python)
- Git

### 🔧 Instalação

1. **Clone o Repositório**
```bash
git clone https://github.com/Gu1lhas04/Nba-Props.git
cd Nba-Props
```

2. **Configure o Ambiente Virtual**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. **Instale as Dependências**
```bash
pip install -r requirements.txt
```

4. **Configure a Base de Dados**
```bash
# Crie uma base de dados PostgreSQL
createdb nba_betting

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o ficheiro .env com as suas configurações
```

5. **Execute as Migrações**
```bash
python manage.py makemigrations
python manage.py migrate
```

6. **Crie um Superutilizador (opcional)**
```bash
python manage.py createsuperuser
```

7. **Inicie o Servidor**
```bash
python manage.py runserver
```

## 🔐 Variáveis de Ambiente

Crie um ficheiro `.env` na raiz do projeto:

```env
# Configurações Django
DEBUG=True
SECRET_KEY=sua_chave_secreta
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de Dados
DATABASE_URL=postgres://user:password@localhost:5432/nba_betting
```

## 📷 Exemplos Visuais

### Interface Principal
![Interface Principal](docs/images/interface_principal.png)

### Análise de Jogadores
![Análise de Jogadores](docs/images/analise_jogadores.png)

### Gráfico de Performance
![Gráfico de Performance](docs/images/grafico_performance.png)

### Sistema de Previsão
![Sistema de Apostas](docs/images/sistema_previsao.png)



## 🚀 Deployment

### Acesso à Demonstração
A plataforma está disponível para demonstração através do Ngrok:
- **URL de Demonstração**: [Link da Demonstração](https://nbabestprops.ngrok.app)

### Para Aceder à Demonstração
1. Clique no link acima
2. Pode testar todas as funcionalidades sem necessidade de instalação local

### Notas Importantes
- A demonstração utiliza dados reais da NBA API
- As apostas são simuladas (não envolvem dinheiro real)
- A plataforma pode estar temporariamente indisponível durante atualizações

## 🤝 Contribuindo

1. Faça um Fork do projeto
2. Crie uma Branch para a sua Feature (`git checkout -b feature/AmazingFeature`)
3. Commit das suas alterações (`git commit -m 'Add some AmazingFeature'`)
4. Push para a Branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

### Padrões de Código
- Siga o PEP 8 para código Python
- Realize comentários pertinentes no código
- Atualize a documentação quando necessário

## ✒️ Autores

* **Guilherme Silva** - *Desenvolvimento* - [GitHub](https://github.com/Gu1lhas04)

## 📞 Suporte

- Email: guilhermemsilva4@gmail.com
- Issues: [GitHub Issues](https://github.com/Gu1lhas04/Nba-Props/issues)

