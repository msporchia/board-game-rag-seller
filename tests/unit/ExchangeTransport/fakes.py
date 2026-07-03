"""A trivial schema for the ExchangeTransport unit — the transport is schema-agnostic (it only
needs a `validator` callable), so a minimal stand-in keeps these tests independent from any real
chat model (ChatReply/TurnAnalysis/...)."""

from pydantic import BaseModel


class Widget(BaseModel):
    value: int
