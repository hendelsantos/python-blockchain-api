"""Métricas Prometheus e telemetria da aplicação."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest

from blockchain_api.api.realtime import RealtimeManager
from blockchain_api.core.blockchain import Blockchain
from blockchain_api.core.network import NodeManager


class Observability:
    """Registro próprio por aplicação para manter testes e instâncias isolados."""

    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.requests_total = Counter(
            "blockchain_http_requests",
            "Total de requisições HTTP processadas.",
            ("method", "route", "status"),
            registry=self.registry,
        )
        self.request_duration = Histogram(
            "blockchain_http_request_duration_seconds",
            "Duração das requisições HTTP em segundos.",
            ("method", "route"),
            registry=self.registry,
        )
        self.chain_length = Gauge(
            "blockchain_chain_length",
            "Quantidade de blocos na cadeia local.",
            registry=self.registry,
        )
        self.pending_transactions = Gauge(
            "blockchain_pending_transactions",
            "Quantidade de transações pendentes.",
            registry=self.registry,
        )
        self.peer_count = Gauge(
            "blockchain_peer_count",
            "Quantidade de peers registrados.",
            registry=self.registry,
        )
        self.websocket_clients = Gauge(
            "blockchain_websocket_clients",
            "Quantidade de clientes WebSocket conectados.",
            registry=self.registry,
        )

    def record_request(self, *, method: str, route: str, status: int, duration: float) -> None:
        labels = {"method": method, "route": route}
        self.requests_total.labels(**labels, status=str(status)).inc()
        self.request_duration.labels(**labels).observe(duration)

    def update_state(
        self,
        blockchain: Blockchain,
        nodes: NodeManager,
        realtime: RealtimeManager,
    ) -> None:
        self.chain_length.set(len(blockchain.chain))
        self.pending_transactions.set(len(blockchain.pending_transactions))
        self.peer_count.set(len(nodes.peers))
        self.websocket_clients.set(realtime.connection_count)

    def render(self) -> bytes:
        return generate_latest(self.registry)
