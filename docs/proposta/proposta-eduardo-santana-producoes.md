# Proposta Comercial — Photo Manager

**Cliente:** Eduardo Santana Produções
**Fornecedor:** Bruno Dias — CPF 414.078.848-83
**Data de emissão:** 25/04/2026
**Validade da proposta:** 30 dias a partir da data de emissão
**Referência:** PROP-2026-04-001

---

## 1. Apresentação

Esta proposta tem como objetivo formalizar o fornecimento e a implantação do **Photo Manager**, um software desktop de gerenciamento e processamento automatizado de fotos para eventos, com tecnologia de reconhecimento facial.

A solução foi desenvolvida sob medida para fluxos de trabalho de fotografia em eventos, permitindo que o operador capture rostos de referência via webcam, escaneie sessões de fotos e identifique automaticamente todas as imagens em que cada pessoa aparece — eliminando a necessidade de revisão manual foto a foto.

---

## 2. Descrição da Solução

O Photo Manager é uma aplicação web local (executada no próprio computador do cliente, sem necessidade de internet ou servidor externo) com interface moderna acessível pelo navegador. O fluxo é dividido em quatro etapas:

1. **Sessão** — seleção da pasta com as fotos do evento
2. **Captura** — registro dos rostos de referência via webcam
3. **Fotos** — escaneamento automatizado e exibição das imagens correspondentes a cada rosto
4. **Imprimir** — composição final com template personalizado e envio para impressora

---

## 3. Funcionalidades Entregues

### Captura e processamento de rostos
- Captura de rostos via webcam com detecção automática
- Suporte a múltiplos rostos de referência simultâneos
- Algoritmo de reconhecimento facial baseado em `dlib` e `face_recognition` (estado da arte)
- Cache de detecções por imagem (rescans subsequentes em segundos)
- Modos de scan ajustáveis: rápido (padrão) e preciso (rostos pequenos/escuros)

### Gerenciamento de sessões
- Seleção de pasta de fotos via Explorador de Arquivos nativo do Windows
- Histórico das 10 sessões mais recentes com indicadores de quantidade e tempo de processamento
- Suporte a formatos JPG, JPEG e PNG
- Estatísticas de progresso em tempo real durante o scan

### Composição e impressão
- Templates de composição personalizados (footer com logo/marca do evento)
- Modos de enquadramento: cobrir (cover) ou conter (contain)
- Alinhamento vertical configurável (topo, centro, rodapé)
- Suporte a orientação retrato e paisagem por foto
- Envio direto para impressora padrão do sistema

### Interface
- Tema dark e light com toggle visível
- Carrossel de visualização ampliada
- Barra de status com contagem de fotos e matches em tempo real
- Snackbar de notificações
- Layout responsivo otimizado para uso em desktop

### Performance e confiabilidade
- Cache persistente de encodings em disco (rescans não recomputam)
- Progress incremental (crash no meio do scan não perde o trabalho já feito)
- Logs detalhados em pasta dedicada para diagnóstico
- Thumbnails pré-gerados por sessão para navegação fluida
- Suporte opcional a processamento multi-thread (configurável)

---

## 4. Stack Tecnológica

| Componente | Tecnologia |
|---|---|
| Backend | Python 3.10+ com FastAPI e Uvicorn |
| Reconhecimento facial | dlib + face_recognition |
| Processamento de imagem | OpenCV, Pillow, NumPy |
| Frontend | HTML5, CSS3, JavaScript ES2020 (sem dependências externas) |
| Câmera no navegador | MediaPipe Vision |
| Impressão | pywin32 (integração nativa Windows) |
| Servidor | Local (127.0.0.1), porta 8000 |

---

## 5. Requisitos de Hardware e Sistema

### Mínimos
- **Sistema operacional:** Windows 10 (64-bit) ou superior
- **Processador:** Intel Core i5 (8ª geração) ou equivalente AMD Ryzen 5
- **Memória RAM:** 8 GB
- **Armazenamento:** 2 GB livres para a aplicação + espaço adicional para fotos
- **Webcam:** integrada ou USB (resolução mínima 720p)
- **Impressora:** instalada e configurada como padrão no Windows
- **Navegador:** Google Chrome, Microsoft Edge ou Firefox (versão atualizada)

### Recomendados (para volumes acima de 500 fotos por evento)
- **Processador:** Intel Core i7 (10ª geração ou superior) / AMD Ryzen 7
- **Memória RAM:** 16 GB
- **Armazenamento:** SSD com 10 GB livres
- **Webcam:** Full HD (1080p) com boa iluminação no ambiente

---

## 6. Prazo de Entrega e Instalação

| Etapa | Prazo |
|---|---|
| Assinatura da proposta e pagamento da entrada | Dia 0 |
| Agendamento da instalação | Até 3 dias úteis após entrada |
| Instalação presencial ou remota e configuração | 1 dia útil |
| Treinamento operacional (até 2 horas) | Mesmo dia da instalação |
| Início da garantia de 30 dias | Dia da entrega |

**Total: até 5 dias úteis** entre assinatura e operação.

---

## 7. Treinamento Incluso

Está incluso no valor da implantação **uma sessão de treinamento de até 2 horas**, presencial ou via videoconferência, cobrindo:

- Operação do fluxo completo (sessão → captura → fotos → impressão)
- Boas práticas para qualidade de reconhecimento (iluminação, distância, ângulo)
- Gerenciamento de pastas de eventos e organização de arquivos
- Uso dos templates de composição
- Configuração da impressora e troubleshooting básico
- Diagnóstico de problemas via logs

Material de apoio em PDF é entregue ao final da sessão.

---

## 8. Política de Atualizações

- **Correções de bugs durante a garantia (30 dias):** sem custo adicional
- **Correções de bugs após a garantia:** sob demanda, cobradas à parte por hora trabalhada
- **Novas funcionalidades:** orçamento separado, baseado em escopo e estimativa de horas
- **Atualizações de bibliotecas/segurança:** podem ser solicitadas a qualquer momento, cobradas como manutenção sob demanda

---

## 9. Termos Legais

### Propriedade intelectual
O código-fonte da aplicação permanece de propriedade do fornecedor. O cliente recebe **licença de uso perpétua, não exclusiva e intransferível** para uso comercial nos seus próprios eventos.

### Confidencialidade (NDA)
O fornecedor compromete-se a tratar como confidencial qualquer informação, lista de clientes, fotos ou material de eventos a que tenha acesso durante a instalação, treinamento ou suporte. O cliente compromete-se a não redistribuir, sublicenciar ou compartilhar a aplicação com terceiros.

### LGPD (Lei Geral de Proteção de Dados)
A aplicação processa imagens faciais, classificadas como **dados pessoais sensíveis** pela LGPD (Art. 5º, II). É **responsabilidade exclusiva do cliente (controlador dos dados)**:

- Obter consentimento expresso dos titulares (pessoas fotografadas) para captura, processamento e armazenamento das imagens
- Manter registros de consentimento conforme exigido pela ANPD
- Definir e cumprir prazo de retenção das fotos
- Atender solicitações de exclusão por parte dos titulares
- Implementar medidas de segurança no ambiente onde a aplicação opera

A aplicação roda **inteiramente local** (sem envio de dados para nuvem ou terceiros), o que facilita o cumprimento da LGPD, mas a responsabilidade legal permanece do cliente.

### Garantia
A garantia de 30 dias cobre exclusivamente correções de bugs e defeitos de funcionamento. **Não cobre:**
- Falhas decorrentes de alteração não autorizada do código ou da configuração
- Problemas causados por hardware defeituoso, drivers desatualizados ou ambiente de rede
- Mudanças no sistema operacional ou em dependências externas (impressoras, webcams) após a entrega

### Limitação de responsabilidade
A responsabilidade total do fornecedor está limitada ao valor pago pelo cliente nesta proposta. O fornecedor não responde por lucros cessantes, perdas indiretas ou danos a terceiros decorrentes do uso da aplicação.

### Foro
Fica eleito o foro da Comarca de São Paulo/SP para dirimir quaisquer questões oriundas deste contrato, com renúncia expressa a qualquer outro, por mais privilegiado que seja.

---

## 10. Investimento

| Item | Valor |
|---|---|
| Licença de uso perpétua + implantação + treinamento + 30 dias de garantia | **R$ 6.500,00** |

### Forma de pagamento

À escolha do cliente:

**Opção A — À vista**
- R$ 6.500,00 no ato da assinatura (5% de desconto opcional → **R$ 6.175,00**)

**Opção B — Parcelado**
- 50% na assinatura: R$ 3.250,00
- 50% na entrega/instalação: R$ 3.250,00

**Meios aceitos:** PIX, transferência bancária ou boleto.

### Após o período de garantia (a partir do 31º dia)

- **Correções de bugs sob demanda:** R$ 150,00/hora trabalhada
- **Pequenos ajustes e configurações:** R$ 150,00/hora trabalhada
- **Novas funcionalidades:** orçamento à parte mediante escopo

Mínimo de cobrança: **1 hora por chamado**.

---

## 11. Aceite

Para aceitar esta proposta, basta responder a este documento confirmando os termos e o modelo de pagamento escolhido.

A partir da confirmação, o fornecedor enviará os dados bancários e iniciará o agendamento da instalação.

---

## 12. Contato do Fornecedor

**Bruno Dias**
CPF: 414.078.848-83
São Paulo / SP

**Telefone / WhatsApp:** +55 (11) 95448-5244
**E-mail:** dev.brunodias@gmail.com

---

*Esta proposta tem validade de 30 dias contados a partir de 25/04/2026. Após esse prazo, valores e condições estão sujeitos a revisão.*
