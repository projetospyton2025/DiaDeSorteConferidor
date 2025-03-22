// No início do DOMContentLoaded
document.addEventListener('DOMContentLoaded', async function() {
    // Ocultar seção de Jogos Mais Sorteados inicialmente
    const jogosMaisSorteadosSection = document.querySelector('.jogos-mais-sorteados');
    if (jogosMaisSorteadosSection) {
        jogosMaisSorteadosSection.style.display = 'none';
    }
    
    // [resto do código existente]
});




// Variáveis globais
const jogosIncluidos = [];
const jogosSelecionados = new Set();
const numerosSelecionados = new Set();
let conferenciaCancelada = false;
let dadosUltimaConsulta = null;
let mesSelecionado = null;

// Configuração tamanho do lote
const TAMANHO_LOTE = 930;

// Função para extrair dígitos únicos de um conjunto de números
function extrairDigitosUnicos(numeros) {
    const digitosSet = new Set();
    
    numeros.forEach(num => {
        const numStr = String(num).padStart(2, '0');
        for (let i = 0; i < numStr.length; i++) {
            digitosSet.add(numStr[i]);
        }
    });
    
    return {
        digitos: Array.from(digitosSet).sort(),
        quantidade: digitosSet.size
    };
}

// Função para formatar a exibição dos dígitos
function formatarDigitosUsados(numeros) {
    const resultado = extrairDigitosUnicos(numeros);
    return `${resultado.quantidade} (${resultado.digitos.join(', ')})`;
}


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

// Funções do Modal
function setupModal() {
    const modal = document.getElementById('info-modal');
    const openModalBtn = document.getElementById('open-info-modal');
    const closeModalBtn = document.querySelector('.close-modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    
    // Abrir modal
    openModalBtn.addEventListener('click', () => {
        modal.style.display = 'block';
    });
    
    // Fechar modal com o X
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }
    
    // Fechar modal com o botão Entendi
    if (modalCloseBtn) {
        modalCloseBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }
    
    // Fechar modal clicando fora
    window.addEventListener('click', (event) => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
    
    // Mostrar o modal automaticamente na primeira visita
    const primeiraVisita = !localStorage.getItem('visitouDiaDeSorte');
    if (primeiraVisita) {
        modal.style.display = 'block';
        localStorage.setItem('visitouDiaDeSorte', 'true');
    }
}

// Análise de dígitos
// Função para analisar dígitos
function analisarDigitos() {
    const digitosAnalise = document.getElementById('digitos-analise');
    
    if (numerosSelecionados.size > 0) {
        digitosAnalise.style.display = 'block';
        
        // Resetar todos os dígitos
        for (let i = 0; i < 10; i++) {
            const digitoEl = document.getElementById(`digito-${i}`);
            digitoEl.classList.remove('digito-presente');
        }
        
        // Análise de dígitos usados
        const analiseDigitos = extrairDigitosUnicos(Array.from(numerosSelecionados));
        
        // Atualizar contagem de dígitos no painel
        const contadorDigitos = document.getElementById('contador-digitos');
        if (contadorDigitos) {
            contadorDigitos.textContent = analiseDigitos.quantidade;
        }
        
        // Marcar dígitos presentes
        analiseDigitos.digitos.forEach(digito => {
            const digitoEl = document.getElementById(`digito-${digito}`);
            if (digitoEl) {
                digitoEl.classList.add('digito-presente');
            }
        });
    } else {
        digitosAnalise.style.display = 'none';
    }
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

    // Configuração dos números
    const numeros = document.querySelectorAll('.numero');
    numeros.forEach(numero => {
        numero.addEventListener('click', () => {
            const num = parseInt(numero.dataset.numero);
            if (numero.classList.contains('selecionado')) {
                numero.classList.remove('selecionado');
                numerosSelecionados.delete(num);
            } else if (numerosSelecionados.size < 7) {
                numero.classList.add('selecionado');
                numerosSelecionados.add(num);
            } else {
                alert('Você já selecionou 7 números!');
            }
            
            // Analisar dígitos após cada seleção/remoção
            analisarDigitos();
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

            // Analisar dígitos do primeiro jogo carregado
            if (data.jogos.length > 0 && data.jogos[0].numeros) {
                analisarDigitosJogoCarregado(data.jogos[0].numeros);
            }

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

// Função para analisar dígitos de jogos carregados
// Função para analisar dígitos de jogos carregados
function analisarDigitosJogoCarregado(numeros) {
    const digitosAnalise = document.getElementById('digitos-analise');
    digitosAnalise.style.display = 'block';
    
    // Resetar todos os dígitos
    for (let i = 0; i < 10; i++) {
        const digitoEl = document.getElementById(`digito-${i}`);
        digitoEl.classList.remove('digito-presente');
    }
    
    // Análise de dígitos usados
    const analiseDigitos = extrairDigitosUnicos(numeros);
    
    // Atualizar contagem de dígitos no painel
    const contadorDigitos = document.getElementById('contador-digitos');
    if (contadorDigitos) {
        contadorDigitos.textContent = analiseDigitos.quantidade;
    }
    
    // Marcar dígitos presentes
    analiseDigitos.digitos.forEach(digito => {
        const digitoEl = document.getElementById(`digito-${digito}`);
        if (digitoEl) {
            digitoEl.classList.add('digito-presente');
        }
    });
}

// Funções de manipulação de jogos
function adicionarJogoNaLista(jogo) {
    const jogoItem = document.createElement('div');
    jogoItem.className = 'jogo-item';

    // Análise de dígitos para este jogo
    const analiseDigitos = extrairDigitosUnicos(jogo.numeros);

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

    const jogoInfo = document.createElement('div');
    jogoInfo.className = 'jogo-info';
    
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
    
    // Adicionar informação de dígitos
    const digitosInfo = document.createElement('div');
    digitosInfo.className = 'jogo-digitos';
    digitosInfo.innerHTML = `<span>Dígitos: <strong>${analiseDigitos.quantidade}</strong> (${analiseDigitos.digitos.join(', ')})</span>`;
    
    jogoInfo.appendChild(jogoNumeros);
    jogoInfo.appendChild(digitosInfo);

    const btnRemover = document.createElement('button');
    btnRemover.className = 'btn-remover';
    btnRemover.textContent = 'Remover';
    btnRemover.onclick = () => removerJogo(jogo, jogoItem);

    // Botão para analisar dígitos do jogo
    const btnAnalisar = document.createElement('button');
    btnAnalisar.className = 'btn-analisar';
    btnAnalisar.innerHTML = '<i class="fas fa-search"></i>';
    btnAnalisar.title = 'Analisar dígitos deste jogo';
    btnAnalisar.onclick = (e) => {
        e.stopPropagation();
        analisarDigitosJogoCarregado(jogo.numeros);
    };

    const botoesContainer = document.createElement('div');
    botoesContainer.className = 'jogo-botoes';
    botoesContainer.appendChild(btnAnalisar);
    botoesContainer.appendChild(btnRemover);

    jogoItem.appendChild(checkbox);
    jogoItem.appendChild(jogoInfo);
    jogoItem.appendChild(botoesContainer);
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
    
    const jogosMaisSorteadosSection = document.querySelector('.jogos-mais-sorteados');

    if (!jogos_stats || jogos_stats.length === 0) {
        jogosMaisSorteadosSection.style.display = 'none';
        return;
    }
    
    jogosMaisSorteadosSection.style.display = 'block';

    // Ordenar por total de acertos (decrescente)
    jogos_stats.sort((a, b) => b.total - a.total);
    
    // Limitar a mostrar apenas os 10 jogos mais sorteados
    const jogosMostrar = jogos_stats.slice(0, 10);

    jogosMostrar.forEach(jogo => {
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

    if (!data.acertos || data.acertos.length === 0) {
        detalhesDiv.innerHTML = '<div class="sem-resultados">Nenhum prêmio encontrado para os jogos selecionados.</div>';
        
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 10; // Ajustado para o número correto de colunas
        td.textContent = 'Nenhum prêmio encontrado.';
        td.style.textAlign = 'center';
        td.style.padding = '20px';
        tr.appendChild(td);
        tabelaBody.appendChild(tr);
        return;
    }

    data.acertos.forEach(resultado => {
        // Análise de dígitos para este jogo
        const analiseDigitos = extrairDigitosUnicos(resultado.seus_numeros);
        
        // Verifica se há informações sobre o mês
        const mesSorteado = resultado.mes_sorteado || 'Não informado';
        const seuMes = resultado.seu_mes || 'Não informado';
        
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
                    <p>Mês da Sorte: <strong>${mesSorteado}</strong></p>
                </div>
                <div class="seu-jogo">
                    <h4>Seu Jogo:</h4>
                    <div class="numeros-lista">
                        ${resultado.seus_numeros
                            .sort((a, b) => a - b)
                            .map(n => `<span class="numero-jogado ${resultado.numeros_sorteados.includes(n) ? 'acerto' : ''}">${String(n).padStart(2, '0')}</span>`)
                            .join(' ')}
                    </div>
                    <p>Seu Mês: <strong>${seuMes}</strong> ${resultado.acertou_mes ? '<span class="acerto-mes">(Acertou!)</span>' : ''}</p>
                </div>
                <div class="resultado-info">
                    <p class="acertos-info">Acertos: <strong>${resultado.acertos}</strong></p>
                    <p class="digitos-info">Dígitos usados: <strong>${analiseDigitos.quantidade}</strong> (${analiseDigitos.digitos.join(', ')})</p>
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
            <td>${mesSorteado}</td>
            <td><div class="numeros-tabela">${seusNumeros}</div></td>
            <td>${seuMes}</td>
            <td>${resultado.acertos}${resultado.acertou_mes ? ' + Mês' : ''}</td>
            <td class="digitos-celula">${analiseDigitos.quantidade} (${analiseDigitos.digitos.join(', ')})</td>
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
    setupModal();
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
        
        // Ocultar análise de dígitos
        document.getElementById('digitos-analise').style.display = 'none';
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
        
        // Analisar dígitos do palpite gerado
        analisarDigitos();
    });

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
        
        // Ocultar análise de dígitos
        document.getElementById('digitos-analise').style.display = 'none';
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
		
		// Resetar barra de progresso
		const progressFill = document.getElementById('progress-fill');
		progressFill.style.width = '0%';
		
		// Limpar logs anteriores
		const logsContainer = document.getElementById('progress-logs');
		if (logsContainer) logsContainer.innerHTML = '';
		
		// Adicionar mensagem inicial
		adicionarLog(`Iniciando conferência de ${jogosIncluidos.length} jogos nos concursos ${inicio} a ${fim}`);
		
		// Configurar timeout para evitar que a requisição fique pendente indefinidamente
		const controlador = new AbortController();
		const timeoutId = setTimeout(() => controlador.abort(), 180000); // 3 minutos
		
		try {
			const response = await fetch('/conferir', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					jogos: jogosIncluidos,
					inicio: inicio,
					fim: fim
				}),
				signal: controlador.signal
			});

			// Limpar o timeout se a resposta chegar
			clearTimeout(timeoutId);
			
			// Verificar se a resposta não é OK
			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.message || 'Erro ao processar jogos');
			}
			
			const resultados = await response.json();
			
			// Verificar se o resultado tem um campo de erro
			if (resultados.error) {
				throw new Error(resultados.message || 'Erro ao processar jogos');
			}
			
			// Garantir que a barra chegue a 100%
			progressFill.style.width = '100%';
			adicionarLog('Processamento concluído com sucesso!');
			
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
			
			// Verificar se é um erro de timeout/abort
			if (error.name === 'AbortError') {
				adicionarLog('ERRO: A requisição demorou muito tempo e foi cancelada.');
				alert('A requisição demorou muito tempo. Tente com um intervalo menor de concursos.');
			} else {
				adicionarLog(`ERRO: ${error.message || 'Erro desconhecido ao processar os jogos'}`);
				alert(`Ocorreu um erro: ${error.message || 'Erro ao processar os jogos. Tente novamente.'}`);
			}
			
			// Garantir que a barra mostre o erro
			progressFill.style.width = '100%';
			progressFill.style.backgroundColor = '#dc3545';
			
		} finally {
			// Limpar timeout se ainda estiver ativo
			clearTimeout(timeoutId);
			
			// Fechar overlay com pequeno delay
			setTimeout(() => {
				if (!conferenciaCancelada) {
					overlay.style.display = 'none';
				}
			}, 1500);
		}
	});
});

function adicionarLog(mensagem) {
    const logDiv = document.createElement('div');
    logDiv.className = 'log-mensagem';
    logDiv.textContent = mensagem;
    const progressText = document.querySelector('.progress-text');
    progressText.appendChild(logDiv);
    // Mantém apenas as últimas 5 mensagens
    while (progressText.children.length > 5) {
        progressText.removeChild(progressText.firstChild);
    }
}

// Função para atualizar visualmente o progresso dos lotes
function atualizarProgressoLote(loteAtual, totalLotes, concursoInicio, concursoFim) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.querySelector('.progress-text');
    const loteInfo = document.createElement('div');
    
    // Calcular porcentagem
    const porcentagem = Math.floor((loteAtual / totalLotes) * 100);
    
    // Atualizar barra
    progressFill.style.width = `${porcentagem}%`;
    
    // Atualizar texto principal
    progressText.textContent = `Processando lote ${loteAtual} de ${totalLotes} (${porcentagem}% concluído)`;
    
    // Adicionar informação detalhada do lote
    loteInfo.className = 'lote-info-card';
    loteInfo.innerHTML = `
        <div class="lote-header">Lote atual: ${loteAtual} de ${totalLotes}</div>
        <div class="lote-details">Concursos: ${concursoInicio} - ${concursoFim}</div>
    `;
    
    // Adicionar à seção de logs
    const logsContainer = document.getElementById('progress-logs');
    if (logsContainer) {
        logsContainer.insertBefore(loteInfo, logsContainer.firstChild);
        
        // Limitar a quantidade de itens
        while (logsContainer.children.length > 10) {
            logsContainer.removeChild(logsContainer.lastChild);
        }
    }
}



// Função melhorada para atualização do progresso
function atualizarProgressoConferencia(loteAtual, totalLotes, concursoInicio, concursoFim) {
    const progressFill = document.getElementById('progress-fill');
    const loteAtualSpan = document.getElementById('lote-atual');
    const totalLotesSpan = document.getElementById('total-lotes');
    const concursoAtualSpan = document.getElementById('concurso-atual');
    const concursoFimSpan = document.getElementById('concurso-fim');
    const progressText = document.querySelector('.progress-text');
    
    // Calcular a porcentagem de progresso
    const progresso = (loteAtual / totalLotes) * 100;
    
    // Atualizar a barra de progresso com animação
    progressFill.style.width = `${progresso}%`;
    progressFill.classList.add('animando');
    
    // Atualizar os textos informativos
    loteAtualSpan.textContent = loteAtual;
    totalLotesSpan.textContent = totalLotes;
    concursoAtualSpan.textContent = concursoInicio;
    concursoFimSpan.textContent = concursoFim;
    
    // Atualizar mensagem de progresso
    progressText.textContent = `Processando lote ${loteAtual} de ${totalLotes}...`;
    
    // Adicionar log visual
    adicionarLog(`Processando concursos ${concursoInicio} a ${concursoFim} (${Math.round(progresso)}% concluído)`);
}

// Função para adicionar logs visuais com timestamp
function adicionarLog(mensagem) {
    const logsContainer = document.getElementById('progress-logs');
    if (!logsContainer) return;
    
    const agora = new Date();
    const timestamp = `${agora.getHours().toString().padStart(2, '0')}:${agora.getMinutes().toString().padStart(2, '0')}:${agora.getSeconds().toString().padStart(2, '0')}`;
    
    const logItem = document.createElement('div');
    logItem.className = 'log-item';
    logItem.innerHTML = `<span class="log-time">${timestamp}</span> ${mensagem}`;
    
    logsContainer.insertBefore(logItem, logsContainer.firstChild);
    
    // Limitar a 5 mensagens mais recentes
    while (logsContainer.children.length > 5) {
        logsContainer.removeChild(logsContainer.lastChild);
    }
    
    // Atualizar a contagem de progresso na title bar para feedback mesmo quando a aba não está focada
    document.title = `(${Math.round(parseFloat(document.getElementById('progress-fill').style.width))}%) Dia de Sorte Conferidor`;
}

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