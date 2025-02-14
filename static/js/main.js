// Variáveis globais
const jogosIncluidos = [];
const jogosSelecionados = new Set();
const numerosSelecionados = new Set();  // Adicionada aqui como global
let conferenciaCancelada = false;
let dadosUltimaConsulta = null;
let mesSelecionado = null;

// Configuração tamanho do lote
const TAMANHO_LOTE = 930;

// Função para atualizar o contador e mensagem
function atualizarContadorJogos() {
    const quantidade = jogosIncluidos.length;
    const contadorElement = document.getElementById('contador-jogos');
    if (contadorElement) {
        contadorElement.textContent = quantidade;
    }

    const tituloJogos = document.querySelector('.jogos-incluidos h3');
    if (tituloJogos) {
        tituloJogos.textContent = `Jogos Incluídos (${quantidade} ${quantidade === 1 ? 'jogo' : 'jogos'})`;
    }
}

// Função para formatar mensagens de jogos
function formatarMensagemJogos(quantidade, acao) {
    if (acao === 'incluir') {
        return `${quantidade} jogo${quantidade === 1 ? ' foi incluído' : 's foram incluídos'} com sucesso!`;
    } else if (acao === 'remover') {
        return `${quantidade} jogo${quantidade === 1 ? ' foi removido' : 's foram removidos'} com sucesso!`;
    }
    return '';
}

// Funções de Drag and Drop
function setupDragAndDrop() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    dropZone.onclick = () => fileInput.click();
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults);
    });
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('dragover');
        });
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('dragover');
        });
    });
    
    dropZone.addEventListener('drop', handleDrop);
    fileInput.addEventListener('change', handleFileSelect);

	// Dentro da função setupDragAndDrop:
    // Configuração dos números
    const numeros = document.querySelectorAll('.numero');
    numeros.forEach(numero => {
        numero.addEventListener('click', () => {
            const num = parseInt(numero.dataset.numero);
            if (numero.classList.contains('selecionado')) {
                numero.classList.remove('selecionado');
                numerosSelecionados.delete(num);
            } else if (numerosSelecionados.size < 7) {  // Alterado de 6 para 7 para o Dia de Sorte
                numero.classList.add('selecionado');
                numerosSelecionados.add(num);
            } else {
                alert('Você já selecionou 7 números!');  // Adicionado alerta
            }
            console.log('Números selecionados:', Array.from(numerosSelecionados));  // Debug
        });
    });

    // Configuração dos meses
    const meses = document.querySelectorAll('.mes');
    meses.forEach(mes => {
        mes.addEventListener('click', () => {
            const mesValor = mes.dataset.mes;
            meses.forEach(m => m.classList.remove('selecionado'));
            if (mesValor === mesSelecionado) {
                mesSelecionado = null;
            } else {
                mes.classList.add('selecionado');
                mesSelecionado = mesValor;
            }
        });
    });
}
function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

async function handleDrop(e) {
    const file = e.dataTransfer.files[0];
    await processFile(file);
}

async function handleFileSelect(e) {
    const file = e.target.files[0];
    await processFile(file);
}

async function processFile(file) {
    if (!file) return;

    const dropZone = document.getElementById('drop-zone');
    dropZone.classList.add('processing');

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/processar_arquivo', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.text();
            throw new Error(errorData);
        }

        const data = await response.json();
        
        if (data.jogos && data.jogos.length > 0) {
            const jogosAtuais = new Set(jogosIncluidos.map(j => JSON.stringify(j)));
            let jogosNovos = 0;

            data.jogos.forEach(jogo => {
                const jogoStr = JSON.stringify(jogo);
                if (!jogosAtuais.has(jogoStr)) {
                    jogosIncluidos.push(jogo);
                    adicionarJogoNaLista(jogo);
                    jogosAtuais.add(jogoStr);
                    jogosNovos++;
                }
            });

            atualizarContadorJogos();
            alert(formatarMensagemJogos(jogosNovos, 'incluir'));
        } else {
            throw new Error('Nenhum jogo válido encontrado');
        }
    } catch (error) {
        console.error('Erro detalhado:', error);
        alert(`Erro ao processar arquivo: ${error.message}`);
    } finally {
        dropZone.classList.remove('processing');
    }
}

// Funções de manipulação de jogos
function adicionarJogoNaLista(jogo) {
    const jogoItem = document.createElement('div');
    jogoItem.className = 'jogo-item';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'jogo-checkbox';
    checkbox.onclick = (e) => {
        const jogoStr = JSON.stringify(jogo);
        if (e.target.checked) {
            jogosSelecionados.add(jogoStr);
            jogoItem.classList.add('selecionado');
        } else {
            jogosSelecionados.delete(jogoStr);
            jogoItem.classList.remove('selecionado');
        }
        atualizarBotoesSeleção();
    };

    const jogoNumeros = document.createElement('div');
    jogoNumeros.className = 'jogo-numeros';
    
    // Números do jogo
    jogo.numeros.forEach(num => {
        const numeroSpan = document.createElement('span');
        numeroSpan.className = 'jogo-numero';
        numeroSpan.textContent = String(num).padStart(2, '0');
        jogoNumeros.appendChild(numeroSpan);
    });

    // Mês, se houver
    if (jogo.mes) {
        const mesSpan = document.createElement('span');
        mesSpan.className = 'jogo-mes';
        mesSpan.textContent = `| ${jogo.mes}`;
        jogoNumeros.appendChild(mesSpan);
    }

    const btnRemover = document.createElement('button');
    btnRemover.className = 'btn-remover';
    btnRemover.textContent = 'Remover';
    btnRemover.onclick = () => removerJogo(jogo, jogoItem);

    jogoItem.appendChild(checkbox);
    jogoItem.appendChild(jogoNumeros);
    jogoItem.appendChild(btnRemover);
    document.getElementById('lista-jogos').appendChild(jogoItem);
}

function removerJogo(jogo, jogoItem) {
    const index = jogosIncluidos.findIndex(j =>
        JSON.stringify(j) === JSON.stringify(jogo)
    );
    if (index !== -1) {
        jogosIncluidos.splice(index, 1);
        jogosSelecionados.delete(JSON.stringify(jogo));
        jogoItem.remove();
        atualizarBotoesSeleção();
        atualizarContadorJogos();
        alert(formatarMensagemJogos(1, 'remover'));
    }
}

function limparTodosJogos() {
    const quantidadeAtual = jogosIncluidos.length;
    if (quantidadeAtual === 0) {
        alert('Não há jogos para remover');
        return;
    }

    if (confirm('Tem certeza que deseja remover todos os jogos?')) {
        jogosIncluidos.length = 0;
        jogosSelecionados.clear();
        document.getElementById('lista-jogos').innerHTML = '';
        atualizarBotoesSeleção();
        atualizarContadorJogos();
        alert(formatarMensagemJogos(quantidadeAtual, 'remover'));
    }
}

function removerJogosSelecionados() {
    if (jogosSelecionados.size === 0) {
        alert('Selecione pelo menos um jogo para remover');
        return;
    }

    const quantidadeRemover = jogosSelecionados.size;
    if (confirm(`Deseja remover ${quantidadeRemover} jogo${quantidadeRemover === 1 ? '' : 's'} selecionado${quantidadeRemover === 1 ? '' : 's'}?`)) {
        jogosSelecionados.forEach(jogoStr => {
            const jogo = JSON.parse(jogoStr);
            const index = jogosIncluidos.findIndex(j =>
                JSON.stringify(j) === jogoStr
            );
            if (index !== -1) {
                jogosIncluidos.splice(index, 1);
            }
        });

        document.querySelectorAll('.jogo-checkbox:checked').forEach(checkbox => {
            checkbox.closest('.jogo-item').remove();
        });

        jogosSelecionados.clear();
        atualizarBotoesSeleção();
        atualizarContadorJogos();
        alert(formatarMensagemJogos(quantidadeRemover, 'remover'));
    }
}

function atualizarBotoesSeleção() {
    const removerSelecionadosBtn = document.getElementById('btn-remover-selecionados');
    if (removerSelecionadosBtn) {
        removerSelecionadosBtn.disabled = jogosSelecionados.size === 0;
    }
}
// Funções de exportação
function toggleBotoesExportacao(mostrar) {
    document.querySelectorAll('.export-buttons').forEach(div => {
        if (mostrar) {
            div.classList.remove('hidden');
        } else {
            div.classList.add('hidden');
        }
    });
}

async function exportarDados(tipo, formato) {
    if (!dadosUltimaConsulta) {
        alert('Faça uma consulta primeiro antes de exportar os dados.');
        return;
    }

    try {
        const response = await fetch(`/exportar/${tipo}/${formato}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(dadosUltimaConsulta)
        });

        if (!response.ok) {
            throw new Error('Erro ao exportar dados');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${tipo}.${formato}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

    } catch (error) {
        console.error('Erro:', error);
        alert('Erro ao exportar os dados. Tente novamente.');
    }
}

// Funções de atualização de interface
function atualizarTabelaJogosSorteados(jogos_stats) {
    const tbody = document.querySelector('#tabela-jogos-sorteados tbody');
    tbody.innerHTML = '';

    jogos_stats.forEach(jogo => {
        const tr = document.createElement('tr');
        
        const tdJogo = document.createElement('td');
        tdJogo.innerHTML = `<div class="numeros-tabela">
            ${jogo.numeros.map(n => 
                `<span class="numero-tabela">${String(n).padStart(2, '0')}</span>`
            ).join('')}
        </div>`;
        
        const tdTotal = document.createElement('td');
        tdTotal.textContent = `${jogo.total} vezes`;
        
        const tdDistribuicao = document.createElement('td');
        const distribuicao = [];
        for (let i = 1; i <= 7; i++) {
            if (jogo.distribuicao[i] > 0) {
                distribuicao.push(
                    `<span class="distribuicao-badge">
                        ${i} ponto${i !== 1 ? 's' : ''}: ${jogo.distribuicao[i]} vez${jogo.distribuicao[i] !== 1 ? 'es' : ''}
                    </span>`
                );
            }
        }
        tdDistribuicao.innerHTML = distribuicao.join(' ');

        const tdMes = document.createElement('td');
        tdMes.textContent = jogo.acertos_mes > 0 ? `${jogo.acertos_mes} vezes` : '-';
        
        tr.appendChild(tdJogo);
        tr.appendChild(tdTotal);
        tr.appendChild(tdDistribuicao);
        tr.appendChild(tdMes);
        tbody.appendChild(tr);
    });
}

function atualizarDetalhesETabela(data) {
    const detalhesDiv = document.getElementById('detalhes-resultados');
    const tabelaBody = document.getElementById('tabela-resultados');
    
    detalhesDiv.innerHTML = '';
    tabelaBody.innerHTML = '';

    data.acertos.forEach(resultado => {
        // Adicionar na seção de detalhes
        const resultadoDiv = document.createElement('div');
        resultadoDiv.className = 'resultado-item';
        resultadoDiv.innerHTML = `
            <div class="resultado-header">
                <h3>Concurso ${resultado.concurso} - ${resultado.data}</h3>
            </div>
            <div class="resultado-numeros">
                <div class="numeros-sorteados">
                    <h4>Números Sorteados:</h4>
                    <div class="numeros-lista">
                        ${resultado.numeros_sorteados
                            .sort((a, b) => a - b)
                            .map(n => `<span class="numero-sorteado">${String(n).padStart(2, '0')}</span>`)
                            .join(' ')}
                    </div>
                    <p>Mês da Sorte: ${resultado.mes_sorteado}</p>
                </div>
                <div class="seu-jogo">
                    <h4>Seu Jogo:</h4>
                    <div class="numeros-lista">
                        ${resultado.seus_numeros
                            .sort((a, b) => a - b)
                            .map(n => `<span class="numero-jogado ${resultado.numeros_sorteados.includes(n) ? 'acerto' : ''}">${String(n).padStart(2, '0')}</span>`)
                            .join(' ')}
                    </div>
                    ${resultado.seu_mes ? `<p>Seu Mês: ${resultado.seu_mes} ${resultado.acertou_mes ? '(Acertou!)' : ''}</p>` : ''}
                </div>
                <div class="resultado-info">
                    <p class="acertos-info">Acertos: <strong>${resultado.acertos}</strong></p>
                    ${resultado.premio > 0 ? 
                        `<p class="premio-info">Prêmio: <strong>R$ ${resultado.premio.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</strong></p>` 
                        : ''}
                </div>
            </div>
        `;
        detalhesDiv.appendChild(resultadoDiv);

        // Adicionar na tabela
        const row = document.createElement('tr');
        const numerosSorteados = resultado.numeros_sorteados
            .sort((a, b) => a - b)
            .map(n => `<span class="numero-tabela">${String(n).padStart(2, '0')}</span>`)
            .join('');
        const seusNumeros = resultado.seus_numeros
            .sort((a, b) => a - b)
            .map(n => `<span class="numero-tabela ${resultado.numeros_sorteados.includes(n) ? 'acerto' : ''}">${String(n).padStart(2, '0')}</span>`)
            .join('');
        const premioText = resultado.premio > 0 
            ? `R$ ${resultado.premio.toLocaleString('pt-BR', {minimumFractionDigits: 2})}` 
            : 'Não houve ganhadores';

        row.innerHTML = `
            <td>${resultado.concurso}</td>
            <td>${resultado.data}</td>
            <td><div class="numeros-tabela">${numerosSorteados}</div></td>
            <td>${resultado.mes_sorteado}</td>
            <td><div class="numeros-tabela">${seusNumeros}</div></td>
            <td>${resultado.seu_mes || '-'}</td>
            <td>${resultado.acertos}${resultado.acertou_mes ? ' + Mês' : ''}</td>
            <td>${premioText}</td>
            <td>${resultado.premio > 0 ? 'Premiado' : 'Acumulado'}</td>
        `;
        tabelaBody.appendChild(row);
    });

    // Atualiza o total no rodapé
    const totalCell = document.querySelector('.total-premios');
    if (totalCell && data.resumo.total_premios) {
        totalCell.textContent = `R$ ${data.resumo.total_premios.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
    }
}
// Inicialização do documento
document.addEventListener('DOMContentLoaded', async function() {
    setupDragAndDrop();
    const numeros = document.querySelectorAll('.numero');
    const limparBtn = document.getElementById('limpar');
    const sugestaoBtn = document.getElementById('sugestao');
    const conferirBtn = document.getElementById('conferir');
    const incluirBtn = document.getElementById('incluir');
    const listaJogos = document.getElementById('lista-jogos');
    const overlay = document.getElementById('overlay');

    
    // Ocultar botões de exportação inicialmente
    toggleBotoesExportacao(false);

    // Configuração do botão de cancelar conferência
    const btnCancelarConferencia = document.getElementById('btn-cancelar-conferencia');
    if (btnCancelarConferencia) {
        btnCancelarConferencia.addEventListener('click', () => {
            conferenciaCancelada = true;
            overlay.style.display = 'none';
        });
    }

    // Configuração dos botões de ação
    document.getElementById('btn-limpar-todos').addEventListener('click', limparTodosJogos);
    document.getElementById('btn-remover-selecionados').addEventListener('click', removerJogosSelecionados);

    // Inicialização
    atualizarContadorJogos();

    // Botão Limpar
    limparBtn.addEventListener('click', () => {
        numeros.forEach(numero => numero.classList.remove('selecionado'));
        numerosSelecionados.clear();
        document.querySelectorAll('.mes').forEach(mes => mes.classList.remove('selecionado'));
        mesSelecionado = null;
    });

    // Botão Sugestão
    sugestaoBtn.addEventListener('click', async () => {
        const response = await fetch('/gerar_numeros');
        const data = await response.json();

        limparBtn.click();
        data.numeros.forEach(num => {
            const numero = document.querySelector(`[data-numero="${num}"]`);
            numero.classList.add('selecionado');
            numerosSelecionados.add(num);
        });
        
        const mesElement = document.querySelector(`[data-mes="${data.mes}"]`);
        if (mesElement) {
            mesElement.classList.add('selecionado');
            mesSelecionado = data.mes;
        }
    });

    // Botão Incluir
   // Botão Incluir
    incluirBtn.addEventListener('click', () => {
        // Debug para verificar os números selecionados
        console.log('Números selecionados ao incluir:', numerosSelecionados);
        
        if (numerosSelecionados.size !== 7) {
            console.log('Quantidade atual:', numerosSelecionados.size); // Debug
            alert(`Selecione 7 números antes de incluir o jogo! (Selecionados: ${numerosSelecionados.size})`);
            return;
        }

        const numerosArray = Array.from(numerosSelecionados).sort((a, b) => a - b);
        console.log('Array de números para incluir:', numerosArray); // Debug
        
        const novoJogo = {
            numeros: numerosArray,
            mes: mesSelecionado
        };

        console.log('Novo jogo a ser incluído:', novoJogo); // Debug

        jogosIncluidos.push(novoJogo);
        adicionarJogoNaLista(novoJogo);
        atualizarContadorJogos();
        alert('1 jogo foi incluído com sucesso!');
        
        // Limpar seleções
        limparBtn.click();
        numerosSelecionados.clear(); // Garantir que o Set está limpo
        mesSelecionado = null;
    });

    // Botão Conferir
    conferirBtn.addEventListener('click', async () => {
        if (jogosIncluidos.length === 0) {
            alert('Inclua pelo menos um jogo antes de conferir!');
            return;
        }

        const inicio = parseInt(document.getElementById('inicio').value);
        const fim = parseInt(document.getElementById('fim').value);

        if (!inicio || !fim || inicio > fim) {
            alert('Verifique os números dos concursos!');
            return;
        }

        overlay.style.display = 'flex';
        conferenciaCancelada = false;
        toggleBotoesExportacao(false);

        try {
            const response = await fetch('/conferir', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    jogos: jogosIncluidos,
                    inicio: inicio,
                    fim: fim
                })
            });

            if (!response.ok) throw new Error('Erro ao processar jogos');
            
            const resultados = await response.json();
            
            // Atualizar contadores
            document.getElementById('quatro-acertos').textContent = resultados.resumo.quatro;
            document.getElementById('cinco-acertos').textContent = resultados.resumo.cinco;
            document.getElementById('seis-acertos').textContent = resultados.resumo.seis;
            document.getElementById('sete-acertos').textContent = resultados.resumo.sete;
            document.getElementById('mes-acertos').textContent = resultados.resumo.mes;

            // Atualizar valores dos prêmios
            const calcularTotalPremios = (acertos) => {
                return resultados.acertos
                    .filter(r => r.acertos === acertos)
                    .reduce((sum, r) => sum + r.premio, 0);
            };

            document.getElementById('quatro-valor').textContent = formatarValor(calcularTotalPremios(4));
            document.getElementById('cinco-valor').textContent = formatarValor(calcularTotalPremios(5));
            document.getElementById('seis-valor').textContent = formatarValor(calcularTotalPremios(6));
            document.getElementById('sete-valor').textContent = formatarValor(calcularTotalPremios(7));
            document.getElementById('mes-valor').textContent = formatarValor(
                resultados.acertos
                    .filter(r => r.acertou_mes)
                    .reduce((sum, r) => sum + r.premio, 0)
            );

            // Atualizar detalhes e tabelas
            atualizarDetalhesETabela(resultados);
            if (resultados.jogos_stats) {
                atualizarTabelaJogosSorteados(resultados.jogos_stats);
            }

            dadosUltimaConsulta = resultados;
            toggleBotoesExportacao(true);

        } catch (error) {
            console.error('Erro:', error);
            alert('Ocorreu um erro ao processar os jogos. Tente novamente.');
        } finally {
            overlay.style.display = 'none';
        }
    });
});

function formatarValor(valor) {
    return valor > 0 ? 
        `R$ ${valor.toLocaleString('pt-BR', {minimumFractionDigits: 2})}` : 
        'Não houve ganhadores';
}

function debugNumeros() {
    console.log('Estado atual dos números selecionados:', {
        quantidade: numerosSelecionados.size,
        numeros: Array.from(numerosSelecionados).sort((a, b) => a - b),
        mes: mesSelecionado
    });
}