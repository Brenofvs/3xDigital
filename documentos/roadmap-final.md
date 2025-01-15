### Roadmap Consolidado do Projeto 3x Digital

Este documento unifica e detalha todas as etapas do roadmap do projeto 3x Digital, alinhando-o às metodologias Kanban ou Scrum. Cada etapa foi dividida em tarefas menores, com placeholders para R$es no modelo PAYC (Paid As You Code), e incorpora os requisitos e funcionalidades detalhados no documento de referência.

---

### **Etapa 1: Setup Inicial**
#### Objetivo
Configurar o ambiente de desenvolvimento, garantir que a infraestrutura inicial esteja pronta e criar a base do projeto.

#### Sprint 1: Duração Estimada - 3 Dias
1. **Configuração do Repositório**:
   - Criar repositório Git.
   - Configurar regras de commit e branch.
   - Estimativa: 0.5 dia.
   - Total: [R$40,00]

2. **Estrutura de Diretórios**:
   - Criar a estrutura de diretórios baseada no design do projeto.
   - Estimativa: 0.5 dia.
   - Total: [R$40,00]

3. **Banco de Dados Inicial**:
   - Implementar o banco de dados SQLite e o script de criação das tabelas.
   - Estimativa: 1 dia.
   - Total: [R$80,00]

4. **CI/CD Básico**:
   - Configurar pipeline inicial (build e testes básicos).
   - Estimativa: 1 dia.
   - Total: [R$80,00]

5. **Revisão e Ajustes Iniciais**:
   - Garantir que todos os componentes configurados estejam funcionais.
   - Estimativa: 1 dia.
   - Total: [R$60,00]

---

### **Etapa 2: Autenticação e Controle de Acesso**
#### Objetivo
Implementar o sistema de autenticação e autorização para proteger dados e diferenciar funções de usuários.

#### Sprint 2: Duração Estimada - 5 Dias
1. **Autenticação com JWT**:
   - Criar endpoints para login e logout.
   - Implementar geração e verificação de tokens JWT.
   - Estimativa: 2 dias.
   - Total: [R$640,00]

2. **Cadastro de Usuários**:
   - Criar endpoint para registro de novos usuários.
   - Estimativa: 1 dia.
   - Total: [R$320,00]

3. **Middleware de Autorização**:
   - Implementar middleware para verificar permissões com base no papel do usuário.
   - Estimativa: 1 dia.
   - Total: [R$320,00]

4. **Testes de Segurança**:
   - Validar autenticação e autorização com testes unitários.
   - Estimativa: 1 dia.
   - Total: [R$320,00]

---

### **Etapa 3: UI/UX Design**
#### Objetivo
Criar protótipos visuais e wireframes para as telas identificadas no projeto.

#### Sprint 3: Duração Estimada - 8 Dias
1. **Design da Tela de Dashboard**:
   - Desenvolver protótipo visual da dashboard com gráficos e métricas.
   - Estimativa: 1 dia.
   - Total: [R$160,00]

2. **Design da Tela de Pedidos**:
   - Criar wireframe para gerenciamento e rastreamento de pedidos.
   - Estimativa: 1 dia.
   - Total: [R$120,00]

3. **Design da Tela de Afiliados**:
   - Prototipar interface para solicitações de afiliados e bloqueios.
   - Estimativa: 1 dia.
   - Total: [R$120,00]

4. **Design das Telas de Produtos/Estoque**:
   - Criar protótipos para cadastro e gerenciamento de estoque.
   - Estimativa: 1 dia.
   - Total: [R$160,00]

5. **Design da Tela de Relatórios**:
   - Desenvolver layouts para relatórios e métricas detalhadas.
   - Estimativa: 1 dia.
   - Total: [R$160,00]

6. **Design das Telas de Ferramentas e Configurações**:
   - Prototipar ferramentas de rastreamento, APIs e interações.
   - Estimativa: 1 dia.
   - Total: [R$120,00]

7. **Design de Funcionários e Banco Virtual**:
   - Prototipar interfaces para gerenciamento de equipes e transações virtuais.
   - Estimativa: 1 dia.
   - Total: [R$200,00]

8. **Design da tela do Aplicativo**:
   - Prototipar interfaces para gerenciamento de equipes e transações virtuais.
   - Estimativa: 1 dia.
   - Total: [R$160,00]

9. **Validação e Ajustes de UI/UX**:
   - Revisar protótipos com base no feedback inicial.
   - Estimativa: 1 dia.
   - Total: [R$160,00]

---

### **Etapa 4: Desenvolvimento Front-End**
#### Objetivo
Implementar as telas e interfaces projetadas no UI/UX Design com funcionalidades interativas.

#### Sprint 4: Duração Estimada - 12 Dias
1. **Implementação da Tela de Dashboard**:
   - Desenvolver interface com gráficos e métricas.
   - Estimativa: 1.5 dias.
   - Total: [R$480,00]

2. **Implementação da Tela de Pedidos**:
   - Criar funcionalidades para gerenciamento e rastreamento de pedidos.
   - Estimativa: 1.5 dias.
   - Total: [R$360,00]

3. **Implementação da Tela de Afiliados**:
   - Desenvolver interface para gerenciamento de solicitações e bloqueios.
   - Estimativa: 1.5 dias.
   - Total: [R$360,00]

4. **Implementação das Telas de Produtos/Estoque**:
   - Criar cadastro de produtos e gestão de estoque.
   - Estimativa: 2 dias.
   - Total: [R$480,00]

5. **Implementação da Tela de Relatórios**:
   - Desenvolver interface para exibição de métricas e exportação de dados.
   - Estimativa: 1.5 dias.
   - Total: [R$480,00]

6. **Implementação das Ferramentas**:
   - Criar páginas para APIs, rastreamento e interações adicionais.
   - Estimativa: 1.5 dias.
   - Total: [R$360,00]

7. **Implementação da Tela de Funcionários**:
   - Criar páginas para APIs, rastreamento e interações adicionais.
   - Estimativa: 1.5 dias.
   - Total: [R$240,00]

8. **Implementação do Banco Virtual**:
   - Criar páginas para APIs, rastreamento e interações adicionais.
   - Estimativa: 1.5 dias.
   - Total: [R$360,00]

9. **Responsividade e Testes Front-End**:
   - Garantir que todas as telas funcionem bem em dispositivos diferentes.
   - Estimativa: 2 dias.
   - Total: [R$240,00]

---

### **Etapa 5: Gestão de Produtos e Categorias**
#### Objetivo
Implementar o núcleo do sistema de produtos e categorias para a gestão de inventário.

#### Sprint 5: Duração Estimada - 6 Dias
1. **CRUD de Produtos**:
   - Criar endpoints para criar, atualizar, deletar e listar produtos.
   - Estimativa: 2 dias.
   - Total: [R$720,00]

2. **CRUD de Categorias**:
   - Criar endpoints para criar, atualizar, deletar e listar categorias.
   - Estimativa: 1 dia.
   - Total: [R$360,00]

3. **Relacionamento Produtos-Categorias**:
   - Implementar vinculação de produtos a categorias.
   - Estimativa: 1.5 dias.
   - Total: [R$540,00]

4. **Testes Funcionais**:
   - Criar testes unitários e de integração para os endpoints de produtos e categorias.
   - Estimativa: 1.5 dias.
   - Total: [R$540,00]

---

### **Etapa 6: Gestão de Pedidos**
#### Objetivo
Construir um sistema para gerenciar pedidos e seus itens.

#### Sprint 6: Duração Estimada - 7 Dias
1. **CRUD de Pedidos**:
   - Criar endpoints para criar, atualizar, deletar e listar pedidos.
   - Estimativa: 2 dias.
   - Total: [R$720,00]

2. **Itens do Pedido**:
   - Implementar lógica para adicionar itens a um pedido.
   - Estimativa: 2 dias.
   - Total: [R$720,00]

3. **Status do Pedido**:
   - Implementar atualização de status ("processing", "shipped", etc.).
   - Estimativa: 2 dias.
   - Total: [R$720,00]

4. **Testes Funcionais**:
   - Garantir que a lógica de pedidos funcione corretamente com testes.
   - Estimativa: 1 dia.
   - Total: [R$360,00]

---

### **Etapa 7: Afiliados e Rastreamento**
#### Objetivo
Implementar o sistema de rastreamento de vendas por afiliados e o cálculo de comissões.

#### Sprint 7: Duração Estimada - 6 Dias
1. **Links de Afiliados**:
   - Implementar geração de links de afiliados com códigos únicos.
   - Estimativa: 1.5 dias.
   - Total: [R$540,00]

2. **Rastreamento de Vendas**:
   - Adicionar lógica para rastrear vendas realizadas a partir de links de afiliados.
   - Estimativa: 2 dias.
   - Total: [R$720,00]

3. **Cálculo de Comissões**:
   - Implementar lógica para calcular comissões baseadas nas vendas atribuídas.
   - Estimativa: 1.5 dias.
   - Total: [R$540,00]

4. **Testes de Rastreamento**:
   - Validar a lógica de rastreamento e cálculo de comissões com testes.
   - Estimativa: 1 dia.
   - Total: [R$360,00]

---

### **Etapa 8: Aplicativo Móvel**
#### Objetivo
Desenvolver o aplicativo móvel, garantindo acesso a funcionalidades-chave da plataforma 3x Digital.

#### Sprint 8: Duração Estimada - 6 Dias
1. **Integração com API REST**:
   - Configurar endpoints do back-end para o app móvel.
   - Estimativa: 2 dias.
   - Total: [R$720,00]

2. **Notificações Push**:
   - Implementar envio e recepção de push notifications usando Firebase Cloud Messaging.
   - Estimativa: 1.5 dias.
   - Total: [R$540,00]

3. **Interface Simplificada**:
   - Desenvolver telas responsivas e otimizadas para dispositivos móveis.
   - Estimativa: 2 dias.
   - Total: [R$720,00]

4. **Testes de Performance e Usabilidade**:
   - Garantir que o aplicativo seja rápido, intuitivo e responsável em diferentes dispositivos.
   - Estimativa: 1 dia.
   - Total: [R$360,00]

---

### **Etapa 9: Financeiro**
#### Objetivo
Criar a base para gerenciar pagamentos e repasses financeiros.

#### Sprint 9: Duração Estimada - 7 Dias
1. **Integração com Gateways**:
   - Configurar integração com gateways de pagamento (e.g., Stripe, Mercado Pago).
   - Estimativa: 2 dias.
   - Total: [R$720,00]

2. **Split de Pagamentos**:
   - Implementar lógica para dividir pagamentos entre afiliados e loja.
   - Estimativa: 2.5 dias.
   - Total: [R$900,00]

3. **Relatórios Financeiros**:
   - Criar endpoints para gerar relatórios financeiros (saldo, transações).
   - Estimativa: 1.5 dias.
   - Total: [R$540,00]

4. **Testes de Transações**:
   - Validar segurança e precisão das transações com testes.
   - Estimativa: 1 dia.
   - Total: [R$360,00]

---

### **Etapa 10: Dashboards e Relatórios**
#### Objetivo
Fornecer visualizações e relatórios detalhados para usuários do sistema.

#### Sprint 10: Duração Estimada - 6 Dias
1. **Dashboard de Admin**:
   - Criar painéis para visualização de métricas gerais.
   - Estimativa: 2 dias.
   - Total: [R$720,00]

2. **Dashboard de Afiliados**:
   - Implementar painéis com foco em vendas e comissões.
   - Estimativa: 1.5 dias.
   - Total: [R$540,00]

3. **Exportação de Relatórios**:
   - Adicionar funcionalidade para exportar relatórios em PDF e Excel.
   - Estimativa: 1.5 dias.
   - Total: [R$540,00]

4. **Testes de Visualização**:
   - Validar os gráficos e relatórios gerados.
   - Estimativa: 1 dia.
   - Total: [R$360,00]

---

### **Etapa 11: Teste e Deploy**
#### Objetivo
Garantir que o sistema esteja funcional, seguro e pronto para produção.

#### Sprint 11: Duração Estimada - 5 Dias
1. **Testes Finais**:
   - Executar testes de carga, segurança e integração.
   - Estimativa: 2 dias.
   - Total: [R$480,00]

2. **Deploy Controlado**:
   - Configurar deploy blue-green ou canary em produção.
   - Estimativa: 1.5 dias.
   - Total: [R$360,00]

3. **Documentação**:
   - Finalizar documentação técnica e de usuário.
   - Estimativa: 1 dia.
   - Total: [R$240,00]

4. **Monitoramento**:
   - Configurar monitoramento com ferramentas como Grafana e Prometheus.
   - Estimativa: 0.5 dia.
   - Total: [R$120,00]

---

### Resumo Consolidado

| Etapa                        | Horas Totais | R$ Total |
|------------------------------|--------------|-------------|
| Setup Inicial                | 30 horas     | [R$300,00]     |
| Autenticação e Controle      | 40 horas     | [R$1.600,00]     |
| UI/UX Design                 | 74 horas     | [R$1,480,00]     |
| Desenvolvimento Front-End    | 140 horas    | [R$4.200,00]     |
| Gestão de Produtos e Categorias | 48 horas  | [R$2.160,00]     |
| Gestão de Pedidos            | 56 horas     | [R$2.520,00]     |
| Afiliados e Rastreamento     | 48 horas     | [R$2.160,00]     |
| Aplicativo Móvel             | 60 horas     | [R$2.700,00]     |
| Financeiro                   | 56 horas     | [R$2.520,00]     |
| Dashboards e Relatórios      | 48 horas     | [R$2.160,00]     |
| Teste e Deploy               | 40 horas     | [R$R$1.200,00]     |
| **Total**                    | **578 horas**| **[R$22.600,00]**|

---